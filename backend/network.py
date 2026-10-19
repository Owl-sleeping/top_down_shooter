"""TCPソケットによる送受信を扱うネットワーク層。"""

import json
import queue
import socket
import struct
import threading

Message = dict


class Connection:

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.incoming: "queue.Queue[Message]" = queue.Queue()
        self._send_lock = threading.Lock()
        self.connected = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def send(self, obj: Message) -> None:
        if not self.connected:
            return
        payload = json.dumps(obj).encode("utf-8")
        header = struct.pack(">I", len(payload))
        try:
            with self._send_lock:
                self.sock.sendall(header + payload)
        except OSError:
            self.connected = False

    def _recv_loop(self) -> None:
        buf = bytearray()
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                while len(buf) >= 4:
                    (length,) = struct.unpack(">I", buf[:4])
                    if len(buf) < 4 + length:
                        break
                    payload = bytes(buf[4:4 + length])
                    del buf[:4 + length]
                    self.incoming.put(json.loads(payload.decode("utf-8")))
        except OSError:
            pass
        finally:
            self.connected = False

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
        try:
            self.sock.close()
        except OSError:
            pass


class Host:
    def __init__(self, port: int) -> None:
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind(("0.0.0.0", port))
        self.listen_sock.listen(1)

    def accept(self, poll_timeout: float = 0.1) -> Connection | None:
        self.listen_sock.settimeout(poll_timeout)
        try:
            client_sock, _addr = self.listen_sock.accept()
        except socket.timeout:
            return None
        return Connection(client_sock)

    def close(self) -> None:
        self.listen_sock.close()


class Client:
    @staticmethod
    def connect(host_ip: str, port: int, timeout: float = 5.0) -> Connection:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host_ip, port))
        sock.settimeout(None)
        return Connection(sock)
