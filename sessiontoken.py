#!/usr/bin/env python3
# server.py - LAN chat server with UDP discovery
"""
Usage:
  python server.py --host 0.0.0.0 --port 12345

The server listens for TCP chat clients and also replies to UDP discovery probes
so clients can auto-discover the server on the LAN.

Discovery protocol (UDP):
  - Client sends ASCII "CHAT_DISCOVER_v1" as a UDP broadcast to <udp_port>.
  - Server replies with a single JSON line: {"type":"server_info","port":<tcp_port>}
    The client should use the sender IP address as the server host and the port from JSON.
"""
import socket
import threading
import json
import time
import argparse

DISCOVER_MAGIC = b"CHAT_DISCOVER_v1"
DISCOVER_RESPONSE_TYPE = "server_info"

def send_json(conn, obj):
    data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
    conn.sendall(data)

def recv_lines(sock, buffer):
    try:
        data = sock.recv(4096)
    except ConnectionResetError:
        return None, buffer
    if not data:
        return None, buffer
    buffer.extend(data)
    lines = []
    while True:
        idx = buffer.find(b"\n")
        if idx == -1:
            break
        line = bytes(buffer[:idx]).decode("utf-8", errors="replace")
        del buffer[:idx+1]
        if line.strip():
            lines.append(line)
    return lines, buffer

class ChatServer:
    def __init__(self, host="0.0.0.0", port=12345):
        self.host = host
        self.port = port
        self.udp_port = port + 1  # UDP discovery port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients_lock = threading.Lock()
        self.clients_by_nick = {}     # nick -> (conn, addr)
        self.clients_by_addr = {}     # "ip:port" -> (nick, conn)
        self.running = True

    def start(self):
        # start TCP server
        self.sock.bind((self.host, self.port))
        self.sock.listen(100)
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        # start UDP discovery responder
        t = threading.Thread(target=self._udp_discovery_responder, daemon=True)
        t.start()
        try:
            while True:
                conn, addr = self.sock.accept()
                t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            self.running = False
            self.sock.close()

    def _udp_discovery_responder(self):
        """Respond to UDP discovery probes from clients."""
        try:
            udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # On some platforms binding to '' is fine; use all interfaces
            udpsock.bind(("", self.udp_port))
            print(f"[DISCOVERY] UDP responder bound to port {self.udp_port}")
            while self.running:
                try:
                    data, addr = udpsock.recvfrom(1024)
                except Exception:
                    continue
                if not data:
                    continue
                if data.strip() == DISCOVER_MAGIC:
                    # reply with JSON containing the TCP port (client will use sender IP)
                    resp = json.dumps({"type": DISCOVER_RESPONSE_TYPE, "port": self.port})
                    try:
                        udpsock.sendto(resp.encode("utf-8"), addr)
                        # debug print
                        print(f"[DISCOVERY] Responded to discovery probe from {addr[0]}:{addr[1]}")
                    except Exception:
                        pass
        except Exception as e:
            print("[DISCOVERY] UDP responder failed:", e)

    def broadcast(self, from_nick, text):
        msg = {"type":"broadcast", "from": from_nick, "text": text, "ts": time.time()}
        with self.clients_lock:
            for nick, (conn, addr) in list(self.clients_by_nick.items()):
                try:
                    send_json(conn, msg)
                except Exception:
                    self._disconnect(nick)

    def _disconnect(self, nick):
        with self.clients_lock:
            entry = self.clients_by_nick.pop(nick, None)
            if entry:
                conn, addr = entry
                addrstr = f"{addr[0]}:{addr[1]}"
                self.clients_by_addr.pop(addrstr, None)
                try:
                    conn.close()
                except:
                    pass
                notice = {"type":"system", "text": f"{nick} disconnected", "ts": time.time()}
                for n, (c, a) in list(self.clients_by_nick.items()):
                    try:
                        send_json(c, notice)
                    except Exception:
                        pass

    def handle_client(self, conn, addr):
        addrstr = f"{addr[0]}:{addr[1]}"
        print(f"[CONNECT] {addrstr}")
        buffer = bytearray()
        try:
            lines, buffer = recv_lines(conn, buffer)
            if lines is None:
                conn.close()
                return
            while not lines:
                lines, buffer = recv_lines(conn, buffer)
                if lines is None:
                    conn.close()
                    return
            first = lines[0]
            try:
                obj = json.loads(first)
            except Exception:
                send_json(conn, {"type":"error", "text":"Invalid registration format."})
                conn.close()
                return
            if obj.get("type") != "register" or not obj.get("nick"):
                send_json(conn, {"type":"error", "text":"First message must be register with a nick."})
                conn.close()
                return
            nick = obj["nick"].strip()
            if not nick:
                send_json(conn, {"type":"error", "text":"Empty nick not allowed."})
                conn.close()
                return
            with self.clients_lock:
                if nick in self.clients_by_nick:
                    send_json(conn, {"type":"error", "text":"Nickname already in use."})
                    conn.close()
                    return
                self.clients_by_nick[nick] = (conn, addr)
                self.clients_by_addr[addrstr] = (nick, conn)
            send_json(conn, {"type":"system", "text":f"Registered as {nick}", "ts": time.time()})
            join_msg = {"type":"system", "text": f"{nick} joined the chat", "ts": time.time()}
            with self.clients_lock:
                for n, (c, a) in list(self.clients_by_nick.items()):
                    if n == nick: continue
                    try:
                        send_json(c, join_msg)
                    except Exception:
                        pass

            remaining = lines[1:]
            for line in remaining:
                self._process_client_json(nick, conn, addr, line)

            while True:
                lines, buffer = recv_lines(conn, buffer)
                if lines is None:
                    break
                for line in lines:
                    self._process_client_json(nick, conn, addr, line)
        except Exception:
            pass
        finally:
            print(f"[DISCONNECT] {addrstr}")
            with self.clients_lock:
                entry = self.clients_by_addr.get(addrstr)
                if entry:
                    nick, c = entry
                    self._disconnect(nick)
            try:
                conn.close()
            except:
                pass

    def _process_client_json(self, nick, conn, addr, json_line):
        try:
            obj = json.loads(json_line)
        except Exception:
            send_json(conn, {"type":"error", "text":"Invalid JSON."})
            return
        typ = obj.get("type")
        if typ == "broadcast":
            text = obj.get("text","")
            print(f"[{nick}] (global): {text}")
            self.broadcast(nick, text)
        elif typ == "private":
            target = obj.get("target")
            text = obj.get("text","")
            print(f"[{nick}] -> {target}: {text}")
            self._route_private(nick, target, text, conn)
        elif typ == "nick":
            newnick = obj.get("nick","").strip()
            if not newnick:
                send_json(conn, {"type":"error", "text":"Empty nickname not allowed."})
                return
            with self.clients_lock:
                if newnick in self.clients_by_nick:
                    send_json(conn, {"type":"error", "text":"Nickname already in use."})
                    return
                old = nick
                self.clients_by_nick.pop(old, None)
                self.clients_by_nick[newnick] = (conn, addr)
                addrstr = f"{addr[0]}:{addr[1]}"
                self.clients_by_addr[addrstr] = (newnick, conn)
            send_json(conn, {"type":"system", "text":f"Nickname changed to {newnick}", "ts":time.time()})
            notice = {"type":"system", "text":f"{old} is now {newnick}", "ts":time.time()}
            with self.clients_lock:
                for n,(c,a) in list(self.clients_by_nick.items()):
                    if n == newnick: continue
                    try: send_json(c, notice)
                    except: pass
        elif typ == "list":
            with self.clients_lock:
                users = [{"nick":n, "addr": f"{a[0]}:{a[1]}"} for n,(c,a) in self.clients_by_nick.items()]
            send_json(conn, {"type":"list", "users": users})
        else:
            send_json(conn, {"type":"error", "text":"Unknown message type."})

    def _route_private(self, from_nick, target, text, from_conn):
        with self.clients_lock:
            if ":" in target:
                entry = self.clients_by_addr.get(target)
                if not entry:
                    send_json(from_conn, {"type":"error", "text":f"No user with address {target} connected."})
                    return
                to_nick, to_conn = entry
            else:
                to = self.clients_by_nick.get(target)
                if not to:
                    send_json(from_conn, {"type":"error", "text":f"No user named {target} connected."})
                    return
                to_conn, _addr = to
                to_nick = target
        pm = {"type":"private", "from": from_nick, "text": text, "ts": time.time()}
        try:
            send_json(to_conn, pm)
            send_json(from_conn, {"type":"system", "text": f"Sent private to {to_nick}", "ts":time.time()})
        except Exception:
            send_json(from_conn, {"type":"error", "text":"Failed to deliver message."})

def main():
    parser = argparse.ArgumentParser(description="LAN chat server with discovery")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()
    server = ChatServer(host=args.host, port=args.port)
    server.start()

if __name__ == "__main__":
    main()
