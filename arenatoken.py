# server.py
# LAN multiplayer server for a simple arena game with UDP discovery, player HP, and bullets.
# Run: python server.py

import socket
import threading
import json
import time
import random
import math

HOST = "0.0.0.0"
PORT = 5000
DISCOVERY_PORT = 5001   # UDP beacon port
BROADCAST_FPS = 20.0    # how many times per second server broadcasts states
TICK_RATE = 60.0        # server physics tick rate

next_id = 1
next_id_lock = threading.Lock()

clients = {}  # client_socket -> player_id
players = {}  # player_id -> {name, x, y, color, last_seen, hp, kills}
players_lock = threading.Lock()

bullets = []  # list of bullet dicts: {id, x, y, vx, vy, owner, ttl}
bullets_lock = threading.Lock()
next_bullet_id = 1
next_bullet_lock = threading.Lock()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def recv_lines(conn, buf):
    try:
        data = conn.recv(4096)
    except Exception:
        return None, buf
    if not data:
        return None, buf
    buf += data.decode('utf-8', errors='ignore')
    lines = []
    while '\n' in buf:
        line, buf = buf.split('\n', 1)
        if line.strip():
            lines.append(line.strip())
    return lines, buf

def handle_client(conn, addr):
    global next_id
    buffer = ""
    player_id = None
    try:
        lines, buffer = recv_lines(conn, "")
        if lines is None:
            conn.close()
            return
        joined = False
        buf = buffer
        while not joined:
            if lines:
                for line in lines:
                    try:
                        msg = json.loads(line)
                        if msg.get("type") == "join":
                            with next_id_lock:
                                player_id = str(next_id)
                                next_id += 1
                            name = msg.get("name", f"Player{player_id}")
                            color = msg.get("color", [255,0,0])
                            with players_lock:
                                players[player_id] = {
                                    "name": name,
                                    "x": 100 + (int(player_id) * 37) % 600,
                                    "y": 100 + (int(player_id) * 23) % 400,
                                    "color": color,
                                    "last_seen": time.time(),
                                    "hp": 100,
                                    "kills": 0
                                }
                                clients[conn] = player_id
                            # send ack with assigned id
                            resp = {"type":"join_ack", "id": player_id}
                            conn.sendall((json.dumps(resp) + '\n').encode('utf-8'))
                            joined = True
                            break
                    except Exception:
                        continue
            if not joined:
                lines, buf = recv_lines(conn, buf)
                if lines is None:
                    conn.close()
                    return

        partial_buf = buf
        while True:
            lines, partial_buf = recv_lines(conn, partial_buf)
            if lines is None:
                break
            for line in lines:
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                mtype = msg.get("type")
                if mtype == "update":
                    x = msg.get("x")
                    y = msg.get("y")
                    with players_lock:
                        if player_id in players:
                            try:
                                players[player_id]["x"] = float(x)
                                players[player_id]["y"] = float(y)
                                players[player_id]["last_seen"] = time.time()
                            except Exception:
                                pass
                elif mtype == "shoot":
                    dx = msg.get("dx", 0.0)
                    dy = msg.get("dy", 0.0)
                    spawn_bullet_for(player_id, dx, dy)
                elif mtype == "quit":
                    raise ConnectionResetError()
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        pass
    finally:
        conn.close()
        with players_lock:
            if conn in clients:
                pid = clients.pop(conn)
                players.pop(pid, None)
        print(f"Connection closed: {addr}")

def spawn_bullet_for(player_id, dx, dy):
    global next_bullet_id
    # normalize direction
    mag = math.hypot(dx, dy)
    if mag <= 0.0001:
        return
    nx, ny = dx / mag, dy / mag
    speed = 420.0  # px/sec
    with players_lock:
        p = players.get(player_id)
        if not p:
            return
        sx = p["x"]
        sy = p["y"]
    with next_bullet_lock:
        bid = str(next_bullet_id)
        next_bullet_id += 1
    b = {"id": bid, "x": sx + nx*20, "y": sy + ny*20, "vx": nx*speed, "vy": ny*speed, "owner": player_id, "ttl": 2.5}
    with bullets_lock:
        bullets.append(b)

def accept_thread(sock):
    print(f"Server (TCP) listening on {HOST}:{PORT}")
    while True:
        try:
            conn, addr = sock.accept()
            print("Client connected from", addr)
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            print("Accept error:", e)

def physics_tick(dt):
    # move bullets, handle collisions
    remove_bullets = []
    with bullets_lock:
        for b in bullets:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["ttl"] -= dt
            if b["ttl"] <= 0:
                remove_bullets.append(b["id"])
    if remove_bullets:
        with bullets_lock:
            bullets[:] = [bb for bb in bullets if bb["id"] not in remove_bullets]

    # check bullet-player collisions
    to_remove = []
    hits = []  # list of (bullet_owner, victim_id)
    with bullets_lock:
        snapshot_bullets = list(bullets)
    with players_lock:
        for b in snapshot_bullets:
            bx, by = b["x"], b["y"]
            owner = b["owner"]
            for pid, p in players.items():
                if pid == owner:
                    continue
                # simple circle collision (player radius 16)
                dx = bx - p["x"]
                dy = by - p["y"]
                if dx*dx + dy*dy <= (16*16):
                    # hit
                    hits.append( (b["id"], owner, pid) )
    if hits:
        with bullets_lock:
            bullets[:] = [bb for bb in bullets if bb["id"] not in {h[0] for h in hits}]
        with players_lock:
            for bid, owner, victim in hits:
                v = players.get(victim)
                if not v:
                    continue
                v["hp"] -= 25
                if v["hp"] <= 0:
                    # owner gets a kill
                    if owner in players:
                        players[owner]["kills"] = players[owner].get("kills",0) + 1
                    # respawn victim
                    players[victim]["hp"] = 100
                    players[victim]["x"] = 50 + random.random()*700
                    players[victim]["y"] = 50 + random.random()*500

def broadcast_loop():
    interval = 1.0 / BROADCAST_FPS
    while True:
        time.sleep(interval)
        with players_lock:
            snapshot = {pid: {"name": p["name"], "x": p["x"], "y": p["y"], "color": p["color"], "hp": p.get("hp",100), "kills": p.get("kills",0)} for pid,p in players.items()}
            conns = list(clients.keys())
        with bullets_lock:
            bcopy = [ {"id": b["id"], "x": b["x"], "y": b["y"], "owner": b["owner"]} for b in bullets ]
        if not conns:
            continue
        msg = {"type":"state", "players": snapshot, "bullets": bcopy, "time": time.time()}
        data = (json.dumps(msg) + '\n').encode('utf-8')
        for conn in conns:
            try:
                conn.sendall(data)
            except Exception:
                pass

def reap_inactive():
    while True:
        time.sleep(5)
        now = time.time()
        to_remove = []
        with players_lock:
            for pid, p in list(players.items()):
                if now - p.get("last_seen", 0) > 12:
                    to_remove.append(pid)
            if to_remove:
                remove_conns = []
                for conn, pidc in list(clients.items()):
                    if pidc in to_remove:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        remove_conns.append(conn)
                for conn in remove_conns:
                    clients.pop(conn, None)
                for pid in to_remove:
                    players.pop(pid, None)
                if to_remove:
                    print("Reaped inactive players:", to_remove)

def discovery_beacon():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    local_ip = get_local_ip()
    payload = {"type":"server_announce", "host": local_ip, "tcp_port": PORT, "name": "PyArenaServer"}
    b = (json.dumps(payload)).encode('utf-8')
    print(f"Discovery beacon running (UDP port {DISCOVERY_PORT}) advertising {local_ip}:{PORT}")
    while True:
        try:
            udp.sendto(b, ('<broadcast>', DISCOVERY_PORT))
        except Exception:
            try:
                udp.sendto(b, ('255.255.255.255', DISCOVERY_PORT))
            except Exception:
                pass
        time.sleep(1.0)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(100)

    t = threading.Thread(target=accept_thread, args=(sock,), daemon=True)
    t.start()
    b = threading.Thread(target=broadcast_loop, daemon=True)
    b.start()
    r = threading.Thread(target=reap_inactive, daemon=True)
    r.start()
    d = threading.Thread(target=discovery_beacon, daemon=True)
    d.start()

    # physics loop
    last = time.time()
    try:
        while True:
            now = time.time()
            dt = now - last
            if dt <= 0:
                time.sleep(0.001)
                continue
            # We can run multiple physics ticks if we fell behind
            max_step = 1.0 / TICK_RATE
            while dt > 0:
                step = min(max_step, dt)
                physics_tick(step)
                dt -= step
            last = now
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("Shutting down server.")
        sock.close()

if __name__ == "__main__":
    main()