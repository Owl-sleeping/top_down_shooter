"""中継サーバー(WebSocket)経由でホストとクライアントをペアリングする接続。

backend.network.Connectionと同じ send()/poll()/connected/close() のインターフェースを
持たせているため、ペアリングが完了した後は game.py 側のコードを一切変更せずに
そのまま使い回せる(Gameクラスは「何らかのConnectionオブジェクト」としてしか扱わない)。
"""

import asyncio
import json
import queue
import threading

import websockets

Message = dict


class RelayConnection:
    def __init__(self) -> None:
        self.incoming: "queue.Queue[Message]" = queue.Queue()
        self.connected = False   # 相手とのペアリングが完了し、対戦通信ができる状態か
        self.failed = False      # ペアリング前に接続が切れた/失敗したか
        self.match_found = False
        self.match_role: str | None = None

        self._loop = asyncio.new_event_loop()
        self._async_outgoing: asyncio.Queue = asyncio.Queue()
        self._ws: "websockets.WebSocketClientProtocol | None" = None
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    # --- game.py から使う同期インターフェース ---

    def send(self, obj: Message) -> None:
        if not self.connected:
            return
        self._loop.call_soon_threadsafe(self._async_outgoing.put_nowait, obj)

    def poll(self) -> list[Message]:
        msgs = []
        while True:
            try:
                msgs.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return msgs

    def close(self) -> None:
        self.connected = False
        ws = self._ws
        if ws is not None:
            asyncio.run_coroutine_threadsafe(ws.close(), self._loop)

    def start_matchmaking(self, url: str) -> None:
        """ランダムマッチの待機を開始し、成立したら役割を受け取る。"""
        asyncio.run_coroutine_threadsafe(self._connect_for_matchmaking(url), self._loop)

    async def _connect_for_matchmaking(self, url: str) -> None:
        try:
            await self._connect(url)
            await self._ws.send(json.dumps({"type": "matchmake"}))
            raw = await self._ws.recv()
            reply = json.loads(raw)
            if reply.get("type") != "matched" or reply.get("role") not in ("host", "client"):
                self.failed = True
                return
            self.match_role = reply["role"]
            self._begin_relay()
            self.match_found = True
        except Exception:
            self.failed = True

    # --- 内部実装 ---

    def _run_blocking(self, coro, timeout: float):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _connect(self, url: str) -> None:
        self._ws = await websockets.connect(url, open_timeout=10)

    async def _request(self, obj: Message) -> Message:
        await self._ws.send(json.dumps(obj))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
        return json.loads(raw)

    def _begin_relay(self) -> None:
        self.connected = True
        asyncio.run_coroutine_threadsafe(self._relay_loop(), self._loop)

    async def _relay_loop(self) -> None:
        recv_task = asyncio.ensure_future(self._recv_forever())
        send_task = asyncio.ensure_future(self._send_forever())
        try:
            await asyncio.wait([recv_task, send_task], return_when=asyncio.FIRST_COMPLETED)
        finally:
            recv_task.cancel()
            send_task.cancel()
            self.connected = False

    async def _recv_forever(self) -> None:
        try:
            async for raw in self._ws:
                self.incoming.put(json.loads(raw))
        except websockets.ConnectionClosed:
            pass

    async def _send_forever(self) -> None:
        try:
            while True:
                obj = await self._async_outgoing.get()
                await self._ws.send(json.dumps(obj))
        except websockets.ConnectionClosed:
            pass

    async def _await_peer_then_relay(self) -> None:
        try:
            raw = await self._ws.recv()
        except websockets.ConnectionClosed:
            self.failed = True
            return
        msg = json.loads(raw)
        if msg.get("type") == "peer_joined":
            self._begin_relay()
        else:
            self.failed = True


def create_room(url: str, timeout: float = 10.0) -> tuple[RelayConnection, str]:
    """ホストとして新しいルームを作る。戻り値: (RelayConnection, 4桁のルームコード)。

    呼び出し直後は conn.connected はまだ False(相手がまだ参加していない)。
    参加者が現れると自動的に conn.connected が True になり、対戦通信が始まる。
    呼び出し側(menu.py)は conn.connected / conn.failed をポーリングして待てばよい。
    """
    conn = RelayConnection()
    try:
        conn._run_blocking(conn._connect(url), timeout)
        reply = conn._run_blocking(conn._request({"type": "host"}), timeout)
    except Exception as exc:
        conn.failed = True
        raise ConnectionError(str(exc)) from exc

    if reply.get("type") != "room_created":
        conn.failed = True
        raise ConnectionError(reply.get("message", "ルーム作成に失敗しました"))

    code = reply["code"]
    asyncio.run_coroutine_threadsafe(conn._await_peer_then_relay(), conn._loop)
    return conn, code


def join_room(url: str, code: str, timeout: float = 10.0) -> RelayConnection:
    """4桁コードでルームに参加する。成功すれば即座にconnected=Trueで返る。"""
    conn = RelayConnection()
    try:
        conn._run_blocking(conn._connect(url), timeout)
        reply = conn._run_blocking(conn._request({"type": "join", "code": code}), timeout)
    except Exception as exc:
        conn.failed = True
        raise ConnectionError(str(exc)) from exc

    if reply.get("type") != "joined":
        conn.failed = True
        raise ConnectionError(reply.get("message", "参加に失敗しました"))

    conn._begin_relay()
    return conn
