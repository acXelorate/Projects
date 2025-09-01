# client.py
# Pygame client that auto-discovers the server via UDP beacon (port 5001)
# Now supports shooting and uses server-assigned id to avoid drawing yourself twice.
# Run: python client.py

import socket
import threading
import json
import time
import pygame as pg
import random
import math
import sys

DISCOVERY_PORT = 5001
TCP_PORT = 5000   # default if server announces different port
UPDATE_FREQUENCY = 20.0  # sends updates ~20 times/sec

# networking state
server_addr = None  # tuple (ip, port)
tcp_sock = None
recv_thread_running = False
players = {}       # pid -> {name, x, y, color, hp}
players_lock = threading.Lock()
bullets = []       # list of bullet dicts {id,x,y,owner}
bullets_lock = threading.Lock()
my_id = None

def discover_server(timeout=4.0):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp.bind(('', DISCOVERY_PORT))
    except Exception:
        try:
            udp.bind(('0.0.0.0', DISCOVERY_PORT))
        except Exception:
            udp.close()
            return None
    udp.settimeout(timeout)
    start = time.time()
    try:
        while True:
            try:
                data, addr = udp.recvfrom(4096)
            except socket.timeout:
                return None
            try:
                msg = json.loads(data.decode('utf-8', errors='ignore'))
                if msg.get("type") == "server_announce":
                    host = msg.get("host") or addr[0]
                    port = int(msg.get("tcp_port", TCP_PORT))
                    return (host, port)
            except Exception:
                pass
            if time.time() - start > timeout:
                return None
    finally:
        udp.close()

def tcp_recv_loop(sock):
    global recv_thread_running, my_id
    recv_thread_running = True
    buf = ""
    try:
        while True:
            try:
                data = sock.recv(4096)
            except Exception:
                break
            if not data:
                break
            buf += data.decode('utf-8', errors='ignore')
            while '\n' in buf:
                line, buf = buf.split('\n', 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.strip())
                except Exception:
                    continue
                mtype = msg.get("type")
                if mtype == "state":
                    with players_lock:
                        players.clear()
                        pmap = msg.get("players", {})
                        for pid, p in pmap.items():
                            players[pid] = {"name": p.get("name","?"), "x": float(p.get("x",0)), "y": float(p.get("y",0)), "color": p.get("color",[255,0,0]), "hp": p.get("hp",100)}
                    with bullets_lock:
                        bullets[:] = msg.get("bullets", [])
                elif mtype == "join_ack":
                    my_id = str(msg.get("id"))
                    print("Assigned id:", my_id)
    finally:
        recv_thread_running = False

def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj) + '\n').encode('utf-8'))
        return True
    except Exception:
        return False

def start_network_connection(host, port, name, color):
    global tcp_sock
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.settimeout(5.0)
    tcp_sock.connect((host, port))
    tcp_sock.settimeout(None)
    join = {"type":"join", "name": name, "color": color}
    send_json(tcp_sock, join)
    t = threading.Thread(target=tcp_recv_loop, args=(tcp_sock,), daemon=True)
    t.start()
    return tcp_sock

# ----------------- Pygame client (arena + shooting) -----------------
def run_game(sock, name, color):
    pg.init()
    screen = pg.display.set_mode((800, 600))
    clock = pg.time.Clock()
    pg.display.set_caption(f"PyArena - {name}")
    # local position (client-predicted)
    x, y = random.randint(50, 750), random.randint(50, 550)
    speed = 200.0  # pixels per second
    last_send = 0.0
    send_interval = 1.0 / UPDATE_FREQUENCY

    running = True
    font = pg.font.SysFont(None, 18)
    while running:
        dt = clock.tick(60) / 1000.0
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                running = False
            elif ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = pg.mouse.get_pos()
                dx = mx - x
                dy = my - y
                # send shoot
                send_json(sock, {"type":"shoot", "dx": dx, "dy": dy})
            elif ev.type == pg.KEYDOWN:
                if ev.key == pg.K_SPACE:
                    mx, my = pg.mouse.get_pos()
                    dx = mx - x
                    dy = my - y
                    send_json(sock, {"type":"shoot", "dx": dx, "dy": dy})

        keys = pg.key.get_pressed()
        dx = dy = 0.0
        if keys[pg.K_w] or keys[pg.K_UP]:
            dy -= 1
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            dy += 1
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            dx -= 1
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            dx += 1
        if dx != 0 and dy != 0:
            mul = (2**0.5)/2.0
            dx *= mul
            dy *= mul
        x += dx * speed * dt
        y += dy * speed * dt
        x = max(10, min(790, x))
        y = max(10, min(590, y))

        now = time.time()
        if now - last_send >= send_interval:
            last_send = now
            try:
                send_json(sock, {"type":"update", "x": x, "y": y})
            except Exception:
                pass

        screen.fill((30,30,30))

        # draw other players from server state (skip our own server-entry if we know my_id)
        with players_lock:
            for pid, p in players.items():
                if my_id is not None and pid == my_id:
                    continue
                col = tuple(int(c) for c in (p.get("color",[255,0,0])))
                pg.draw.circle(screen, col, (int(p["x"]), int(p["y"])), 16)
                name_surf = font.render(p.get("name",""), True, (240,240,240))
                screen.blit(name_surf, (p["x"] - name_surf.get_width()//2, p["y"] - 24))
                # hp bar
                hp = p.get("hp",100)
                hp_w = 32 * (max(0, min(100, hp)) / 100.0)
                pg.draw.rect(screen, (60,60,60), (p["x"]-16, p["y"]+18, 32, 6))
                pg.draw.rect(screen, (200,30,30), (p["x"]-16, p["y"]+18, int(hp_w), 6))

        # draw bullets
        with bullets_lock:
            for b in bullets:
                try:
                    bx = int(b.get("x",0))
                    by = int(b.get("y",0))
                    pg.draw.circle(screen, (240,220,40), (bx, by), 6)
                except Exception:
                    pass

        # draw our local player on top
        try:
            pg.draw.circle(screen, tuple(int(c) for c in color), (int(x), int(y)), 16)
            with players_lock:
                hp = None
                if my_id is not None and my_id in players:
                    hp = players[my_id].get("hp", 100)
            if hp is None:
                hp = 100
            name_surf = font.render(name + " (you)", True, (240,240,240))
            screen.blit(name_surf, (x - name_surf.get_width()//2, y - 24))
            hp_w = 36 * (max(0, min(100, hp)) / 100.0)
            pg.draw.rect(screen, (60,60,60), (x-18, y+18, 36, 8))
            pg.draw.rect(screen, (200,30,30), (x-18, y+18, int(hp_w), 8))
        except Exception:
            pass

        # HUD hint
        hint = font.render("WASD / Arrows to move — LMB or SPACE to shoot toward mouse", True, (200,200,200))
        screen.blit(hint, (8, 8))

        pg.display.flip()

    try:
        send_json(sock, {"type":"quit"})
    except Exception:
        pass
    try:
        sock.close()
    except Exception:
        pass
    pg.quit()

def parse_color_input(s):
    if not s:
        return None
    s = s.strip()
    if s.lower() == 'r' or s.lower() == 'random':
        return None
    parts = s.split(',')
    if len(parts) == 3:
        try:
            r,g,b = [max(0, min(255, int(p))) for p in parts]
            return [r,g,b]
        except Exception:
            return None
    return None

def main():
    print("PyArena client — will try to auto-discover the server on the LAN.")
    print("Listening for server beacons (UDP port {})...".format(DISCOVERY_PORT))
    discovered = discover_server(timeout=4.0)
    server_ip = None
    server_port = TCP_PORT
    if discovered:
        server_ip, server_port = discovered
        print(f"Found server at {server_ip}:{server_port}")
    else:
        print("No server beacon found automatically.")
        manual = input("Type server IP to connect to (or leave blank to use localhost): ").strip()
        if manual:
            server_ip = manual
        else:
            server_ip = '127.0.0.1'
    name = input("Enter your player name (leave blank for random): ").strip()
    if not name:
        name = "Player" + str(random.randint(1000,9999))
    c_in = input("Enter color as r,g,b (or 'random' / leave blank for random): ").strip()
    col = parse_color_input(c_in)
    if col is None:
        col = [random.randint(40,255) for _ in range(3)]

    print(f"Connecting to server {server_ip}:{server_port} as '{name}' with color {col} ...")
    try:
        sock = start_network_connection(server_ip, server_port, name, col)
    except Exception as e:
        print("Failed to connect to server:", e)
        print("Exiting.")
        return
    time.sleep(0.05)
    run_game(sock, name, col)

if __name__ == "__main__":
    main()