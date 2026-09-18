"""4桁のルームコードでホストとクライアントを中継するリレーサーバー。

無料のホスティング(Replit等)にデプロイして常駐させる。ゲーム本体のメッセージ
(map_select/weapon_select/input/action/snapshotなど)の中身は一切解釈せず、
ペアリング後は届いたメッセージをそのまま相手に転送するだけの単純な中継。

これにより、ホスト側のポート開放やCGNATを気にする必要がなくなる
(ホスト・クライアントの双方が、このサーバーへ「発信」接続するだけで済むため)。
"""

import asyncio
import json
import os
import random
import time

import websockets

ROOM_CODE_DIGITS = 4
ROOM_TIMEOUT_SECONDS = 600  # 10分間誰も参加しなければルームを自動的に破棄する

# ルームコード -> ホスト側のWebSocket接続
rooms: dict[str, "websockets.WebSocketServerProtocol"] = {}
room_created_at: dict[str, float] = {}


def _generate_code() -> str:
    while True:
        code = f"{random.randint(0, 10 ** ROOM_CODE_DIGITS - 1):0{ROOM_CODE_DIGITS}d}"
        if code not in rooms:
            return code


async def _pipe(src, dst) -> None:
    try:
        async for message in src:
            await dst.send(message)
    except websockets.ConnectionClosed:
        pass
    finally:
        try:
            await dst.close()
        except websockets.ConnectionClosed:
            pass


async def _relay(host_ws, client_ws) -> None:
    await asyncio.gather(_pipe(host_ws, client_ws), _pipe(client_ws, host_ws))


async def _cleanup_stale_rooms() -> None:
    while True:
        await asyncio.sleep(60)
        now = time.time()
        stale = [code for code, ts in list(room_created_at.items()) if now - ts > ROOM_TIMEOUT_SECONDS]
        for code in stale:
            ws = rooms.pop(code, None)
            room_created_at.pop(code, None)
            if ws is not None:
                await ws.close()


async def handler(websocket) -> None:
    try:
        raw = await asyncio.wait_for(websocket.recv(), timeout=15)
    except (asyncio.TimeoutError, websockets.ConnectionClosed):
        return

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.close()
        return

    msg_type = msg.get("type")

    if msg_type == "host":
        code = _generate_code()
        rooms[code] = websocket
        room_created_at[code] = time.time()
        await websocket.send(json.dumps({"type": "room_created", "code": code}))
        try:
            await websocket.wait_closed()
        finally:
            rooms.pop(code, None)
            room_created_at.pop(code, None)
        return

    if msg_type == "join":
        code = str(msg.get("code", "")).strip()
        host_ws = rooms.get(code)
        if host_ws is None:
            await websocket.send(json.dumps({"type": "error", "message": "ルームが見つかりません"}))
            return

        del rooms[code]
        room_created_at.pop(code, None)

        await websocket.send(json.dumps({"type": "joined"}))
        await host_ws.send(json.dumps({"type": "peer_joined"}))

        await _relay(host_ws, websocket)
        return

    await websocket.send(json.dumps({"type": "error", "message": "unknown request"}))


async def main() -> None:
    port = int(os.environ.get("PORT", 8765))
    asyncio.create_task(_cleanup_stale_rooms())
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Relay server listening on 0.0.0.0:{port}")
        await asyncio.Future()  # 永久に待機(サーバーを動かし続ける)


if __name__ == "__main__":
    asyncio.run(main())
