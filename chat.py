#!/usr/bin/env python3
# client.py - LAN chat client with startup prompts and auto-discovery
"""
Usage:
  python client.py
  The program will prompt at startup to either auto-discover the server on the LAN
  or let you enter the server host/port and your nickname manually.

Discovery protocol (UDP):
  - Client broadcasts ASCII "CHAT_DISCOVER_v1" to <udp_port> (tcp_port + 1).
  - Server responds with JSON: {"type":"server_info","port":<tcp_port>}
  - Client uses the first reply it receives (sender IP + returned port).
"""
import socket
import threading
import json
import time
import argparse
import sys

DISCOVER_MAGIC = b"CHAT_DISCOVER_v1"
DISCOVER_RESPONSE_TYPE = "server_info"
DISCOVER_TIMEOUT = 1.0  # seconds to wait for discovery replies

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

def discover_server(broadcast_port):
    """Broadcast a discovery probe and return (host, port) of the first responder or None."""
    try:
        udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udpsock.settimeout(DISCOVER_TIMEOUT)
        # Send to the broadcast IPv4 address
        try:
            udpsock.sendto(DISCOVER_MAGIC, ("255.255.255.255", broadcast_port))
        except Exception:
            # Some networks may prefer sending to the subnet broadcast; try generic send anyway
            try:
                udpsock.sendto(DISCOVER_MAGIC, ("<broadcast>", broadcast_port))
            except Exception:
                pass
        start = time.time()
        while True:
            try:
                data, addr = udpsock.recvfrom(1024)
            except socket.timeout:
                return None
            except Exception:
                return None
            if not data:
                continue
            # try parse JSON
            try:
                obj = json.loads(data.decode("utf-8", errors="replace"))
            except Exception:
                continue
            if obj.get("type") == DISCOVER_RESPONSE_TYPE and "port" in obj:
                tcp_port = int(obj["port"])
                server_host = addr[0]  # use sender IP
                return server_host, tcp_port
            # stop if timed out
            if time.time() - start > DISCOVER_TIMEOUT:
                return None
    except Exception:
        return None

class ChatClient:
    def __init__(self, host, port, nick):
        self.server = (host, port)
        self.nick = nick
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.recv_buffer = bytearray()
        self.running = True

    def start(self):
        try:
            print(f"[INFO] Connecting to {self.server[0]}:{self.server[1]} ...")
            self.sock.connect(self.server)
        except Exception as e:
            print(f"[ERROR] Could not connect to {self.server}: {e}")
            return
        send_json(self.sock, {"type":"register", "nick": self.nick})
        t = threading.Thread(target=self._receiver, daemon=True)
        t.start()
        try:
            while self.running:
                line = input()
                if not line:
                    continue
                if line.startswith("/"):
                    self._handle_command(line)
                else:
                    send_json(self.sock, {"type":"broadcast", "text": line})
        except (KeyboardInterrupt, EOFError):
            self._quit()
        finally:
            try:
                self.sock.close()
            except:
                pass

    def _handle_command(self, line):
        parts = line.split(" ", 2)
        cmd = parts[0].lower()
        if cmd == "/msg":
            if len(parts) < 3:
                print("Usage: /msg <nick|ip:port> <message>")
                return
            target = parts[1]
            message = parts[2]
            send_json(self.sock, {"type":"private", "target": target, "text": message})
        elif cmd == "/nick":
            if len(parts) < 2:
                print("Usage: /nick <newnick>")
                return
            newnick = parts[1].strip()
            if not newnick:
                print("Empty nick not allowed.")
                return
            send_json(self.sock, {"type":"nick", "nick": newnick})
            self.nick = newnick
        elif cmd == "/list":
            send_json(self.sock, {"type":"list"})
        elif cmd == "/quit":
            self._quit()
        else:
            print("Unknown command. Available: /msg /nick /list /quit")

    def _quit(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass
        print("Disconnected. Bye.")
        sys.exit(0)

    def _receiver(self):
        try:
            while self.running:
                lines, self.recv_buffer = recv_lines(self.sock, self.recv_buffer)
                if lines is None:
                    print("[INFO] Server disconnected.")
                    self.running = False
                    break
                for line in lines:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        print("[WARN] Received bad JSON.")
                        continue
                    self._handle_server_msg(obj)
        except Exception:
            pass
        finally:
            self.running = False

    def _handle_server_msg(self, obj):
        typ = obj.get("type")
        if typ == "broadcast":
            frm = obj.get("from", "<unknown>")
            text = obj.get("text", "")
            print(f"[{frm}] {text}")
        elif typ == "private":
            frm = obj.get("from","<unknown>")
            text = obj.get("text","")
            print(f"[PM from {frm}] {text}")
        elif typ == "system":
            text = obj.get("text","")
            print(f"[SYSTEM] {text}")
        elif typ == "error":
            text = obj.get("text","")
            print(f"[ERROR] {text}")
        elif typ == "list":
            users = obj.get("users", [])
            print("Connected users:")
            for u in users:
                print(f"  {u.get('nick')} @ {u.get('addr')}")
        else:
            print("[UNKNOWN MSG]", obj)

def startup_prompt():
    print("=== LAN Chat Client ===")
    print("Options:")
    print("  1) Auto-discover server on the local network (recommended)")
    print("  2) Enter server host and port manually")
    print("  3) Quit")
    choice = input("Choose an option [1]: ").strip() or "1"
    if choice not in ("1","2","3"):
        print("Invalid choice, defaulting to 1.")
        choice = "1"
    if choice == "3":
        print("Bye.")
        sys.exit(0)
    if choice == "1":
        # ask for port to probe (the UDP discovery port = tcp_port + 1)
        port_input = input("Enter TCP port the server listens on (default 12345): ").strip() or "12345"
        try:
            tcp_port = int(port_input)
        except:
            tcp_port = 12345
        udp_probe_port = tcp_port + 1
        print(f"[DISCOVERY] Broadcasting discovery probe on UDP port {udp_probe_port} (timeout {DISCOVER_TIMEOUT}s)...")
        found = discover_server(udp_probe_port)
        if found:
            host, port = found
            print(f"[DISCOVERY] Found server at {host}:{port}")
        else:
            print("[DISCOVERY] No server found.")
            # fallback to manual entry
            host = input("Enter server host (IP or hostname): ").strip()
            if not host:
                print("No host provided, exiting.")
                sys.exit(1)
            port_input = input(f"Enter server TCP port (default {tcp_port}): ").strip() or str(tcp_port)
            try:
                port = int(port_input)
            except:
                port = tcp_port
    else:
        host = input("Enter server host (IP or hostname): ").strip()
        if not host:
            print("No host provided, exiting.")
            sys.exit(1)
        port_input = input("Enter server TCP port (default 12345): ").strip() or "12345"
        try:
            port = int(port_input)
        except:
            port = 12345

    nick = input("Choose a nickname: ").strip()
    if not nick:
        print("Nickname required.")
        sys.exit(1)
    return host, port, nick

def main():
    parser = argparse.ArgumentParser(description="LAN chat client with discovery and startup prompts")
    parser.add_argument("--host", help="Server host to connect to (skip prompts)")
    parser.add_argument("--port", type=int, help="Server TCP port (skip prompts)")
    parser.add_argument("--nick", help="Nickname (skip prompts)")
    parser.add_argument("--autodiscover", action="store_true", help="Auto-discover server without interactive prompt")
    args = parser.parse_args()

    if args.host and args.port and args.nick:
        host, port, nick = args.host, args.port, args.nick
    elif args.autodiscover:
        tcp_port = args.port or 12345
        found = discover_server(tcp_port + 1)
        if not found:
            print("[DISCOVERY] No server found, please run with no args to use interactive prompt.")
            sys.exit(1)
        host, port = found
        nick = args.nick or input("Choose a nickname: ").strip()
        if not nick:
            print("Nickname required.")
            sys.exit(1)
    else:
        host, port, nick = startup_prompt()

    client = ChatClient(host=host, port=port, nick=nick)
    client.start()

if __name__ == "__main__":
    main()
