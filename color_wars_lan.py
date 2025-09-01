"""
Color Wars - single-file LAN multiplayer (host or join)

How it works:
- Run this file on both machines.
- On the host machine press H to host. The host will listen on port 50007 and wait for a client.
- On the client machine press J and type the host IP (press Enter to connect).
- Host is player 1 (blue), client is player 2 (red).
- All game logic is authoritative on the host. The client sends click actions to the host; the host applies them and broadcasts the full game state back.

Dependencies: pygame (pip install pygame)

Note: This is a minimal, robust example intended for LAN (same network). Firewall/port forwarding may be needed if machines are on different networks.
"""

import pygame as pg
import threading
import socket
import json
from random import randint
import time

PORT = 50007
BUFSIZE = 4096

pg.init()
pg.font.init()
WIDTH, HEIGHT = 800, 800
window = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("COLOR WARS LAN")
font = pg.font.SysFont(None, 80)
bigfont = pg.font.SysFont(None, 250)
clock = pg.time.Clock()

# --- game state ---
board = [[0]*5 for _ in range(5)]
owner = [[0]*5 for _ in range(5)]
turn = randint(1,2)
redfirst = 1
bluefirst = 1

state_lock = threading.Lock()

# networking
conn = None        # connection socket on host after accept
net_sock = None    # for both host (listener) and client (connected socket)
is_host = False
connected = False
my_id = None       # 1 for host player, 2 for client player

# rectangles
rectlist = []
for y in range(5):
    row = []
    for x in range(5):
        row.append(pg.Rect(x*160, y*160, 160, 160))
    rectlist.append(row)

# helper: send json messages delimited by newline

def send_json(sock, obj):
    try:
        data = json.dumps(obj).encode('utf-8') + b"\n"
        sock.sendall(data)
    except Exception as e:
        print("send error:", e)


def recv_json_stream(sock, callback):
    """Receive newline-delimited JSON and call callback(obj) for each message."""
    buff = b""
    try:
        while True:
            data = sock.recv(BUFSIZE)
            if not data:
                # disconnected
                callback({'type':'disconnect'})
                break
            buff += data
            while b"\n" in buff:
                line, buff = buff.split(b"\n", 1)
                if not line:
                    continue
                try:
                    obj = json.loads(line.decode('utf-8'))
                except Exception as e:
                    print('json decode error', e)
                    continue
                callback(obj)
    except Exception as e:
        print('recv loop error', e)
        callback({'type':'disconnect'})

# game logic functions

def pop(own, r, c):
    global board, owner
    # apply pops relative to r,c
    try:
        if r-1 != -1:
            board[r-1][c] += 1
    except:
        pass
    try:
        board[r+1][c] += 1
    except:
        pass
    try:
        if c-1 != -1:
            board[r][c-1] += 1
    except:
        pass
    try:
        board[r][c+1] += 1
    except:
        pass
    try:
        if r-1 != -1:
            owner[r-1][c] = own
    except:
        pass
    try:
        owner[r+1][c] = own
    except:
        pass
    try:
        if c-1 != -1:
            owner[r][c-1] = own
    except:
        pass
    try:
        owner[r][c+1] = own
    except:
        pass


def apply_click(player_id, r, c):
    """Host validates and applies a click from player_id on cell r,c."""
    global board, owner, turn, redfirst, bluefirst
    with state_lock:
        val = board[r][c]
        own = owner[r][c]
        # initial placement rules
        if turn == 1:
            # player 1's turn
            if bluefirst and val == 0 and player_id == 1:
                owner[r][c] = 1
                board[r][c] = 3
                bluefirst = 0
                turn = 2
                return True
            if own == 1 and player_id == 1:
                board[r][c] = val + 1
                turn = 2
                # handle pop
                if board[r][c] >= 4:
                    board[r][c] = 0
                    owner[r][c] = 0
                    pop(1, r, c)
                return True
        else:
            # player 2's turn
            if redfirst and val == 0 and player_id == 2:
                owner[r][c] = 2
                board[r][c] = 3
                redfirst = 0
                turn = 1
                return True
            if own == 2 and player_id == 2:
                board[r][c] = val + 1
                turn = 1
                if board[r][c] >= 4:
                    board[r][c] = 0
                    owner[r][c] = 0
                    pop(2, r, c)
                return True
    return False


def serialize_state():
    with state_lock:
        return {'type':'state', 'board':board, 'owner':owner, 'turn':turn, 'redfirst':redfirst, 'bluefirst':bluefirst}

# networking callbacks

def host_recv_callback(obj):
    global connected, net_sock
    if obj.get('type') == 'action':
        # client clicked: apply then broadcast state
        r = obj.get('row')
        c = obj.get('col')
        pid = obj.get('player_id')
        applied = apply_click(pid, r, c)
        # after applying, broadcast full state
        if net_sock:
            try:
                send_json(net_sock, serialize_state())
            except:
                pass
    elif obj.get('type') == 'disconnect':
        print('client disconnected')
        connected = False
    else:
        pass


def client_recv_callback(obj):
    global board, owner, turn, redfirst, bluefirst, connected
    if obj.get('type') == 'state':
        with state_lock:
            # replace local state with host authoritative state
            board = obj['board']
            owner = obj['owner']
            turn = obj['turn']
            redfirst = obj['redfirst']
            bluefirst = obj['bluefirst']
            connected = True
    elif obj.get('type') == 'assign':
        # host told us our player id
        global my_id
        my_id = obj.get('player_id')
        connected = True
    elif obj.get('type') == 'disconnect':
        print('host disconnected')
        connected = False

# host thread: accept one client and spawn recv loop

def start_host_thread():
    global net_sock, is_host, conn, connected, my_id
    is_host = True
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", PORT))
    s.listen(1)
    print('Hosting on port', PORT)
    conn, addr = s.accept()
    print('Client connected from', addr)
    net_sock = conn
    # when client connects, assign them player 2
    send_json(net_sock, {'type':'assign', 'player_id':2})
    # send full initial state
    send_json(net_sock, serialize_state())
    connected = True
    my_id = 1
    # start recv loop in thread
    threading.Thread(target=recv_json_stream, args=(net_sock, host_recv_callback), daemon=True).start()

# client connect thread

def start_client_thread(host_ip):
    global net_sock, connected, my_id
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host_ip, PORT))
    except Exception as e:
        print('Failed to connect:', e)
        connected = False
        return
    net_sock = s
    # start receiver
    threading.Thread(target=recv_json_stream, args=(net_sock, client_recv_callback), daemon=True).start()
    my_id = 2
    connected = True

# UI: simple menu to Host/Join and type IP if joining

def show_text_center(text, y, small=False):
    f = font if not small else font
    surf = f.render(text, True, (255,255,255))
    r = surf.get_rect(center=(WIDTH//2, y))
    window.blit(surf, r)


def menu():
    global is_host, net_sock, my_id
    typing = False
    ip_text = ''
    state = 'menu'  # menu, join
    while True:
        window.fill((30,30,30))
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit(); raise SystemExit
            if state == 'menu' and event.type == pg.KEYDOWN:
                if event.key == pg.K_h:
                    # start host thread
                    threading.Thread(target=start_host_thread, daemon=True).start()
                    my_id = 1
                    return
                if event.key == pg.K_j:
                    state = 'join'
                    typing = True
                    ip_text = ''
            elif state == 'join':
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN:
                        # try to connect
                        threading.Thread(target=start_client_thread, args=(ip_text,), daemon=True).start()
                        return
                    elif event.key == pg.K_BACKSPACE:
                        ip_text = ip_text[:-1]
                    else:
                        ip_text += event.unicode
        # draw menu
        window.fill((0,0,0))
        title = bigfont.render('COLOR WARS', True, (200,200,200))
        window.blit(title, (20, 50))
        show_text_center('H - Host (wait for client)', 500)
        show_text_center('J - Join (type host IP)', 560)
        if state == 'join':
            box = font.render('Host IP: ' + ip_text, True, (255,255,255))
            window.blit(box, (50, 640))
        pg.display.update()
        clock.tick(30)

# start menu
menu()

# main game loop
running = True
leftclick = False

# helper to send action from client to host

def client_send_action(r,c):
    if net_sock:
        send_json(net_sock, {'type':'action','player_id':my_id,'row':r,'col':c})

# If this instance is host, we will broadcast state regularly

def host_broadcast_loop():
    global net_sock, connected
    while True:
        time.sleep(0.1)
        if is_host and net_sock and connected:
            try:
                send_json(net_sock, serialize_state())
            except Exception as e:
                print('broadcast error', e)
                connected = False
                break

if is_host:
    threading.Thread(target=host_broadcast_loop, daemon=True).start()

while running:
    mousex, mousey = pg.mouse.get_pos()
    leftclick = False
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                leftclick = True

    # background according to whose turn
    with state_lock:
        cur_turn = turn
    if cur_turn == 2:
        window.fill((200,0,0))
    else:
        window.fill((0,0,200))

    for r in range(5):
        for c in range(5):
            rect = rectlist[r][c]
            with state_lock:
                val = board[r][c]
                own = owner[r][c]
            pg.draw.rect(window, (0,0,0), rect, 1)
            if own == 1:
                txt = bigfont.render(str(val), True, (0,0,150))
                window.blit(txt, rect.topleft)
            elif own == 2:
                txt = bigfont.render(str(val), True, (150,0,0))
                window.blit(txt, rect.topleft)

            if leftclick and rect.collidepoint(mousex, mousey):
                leftclick = False
                # networked logic: if host, apply directly and broadcast
                if is_host:
                    applied = apply_click(my_id, r, c)
                    # host will broadcast shortly in loop, but send imediately too
                    if net_sock and connected:
                        try:
                            send_json(net_sock, serialize_state())
                        except:
                            pass
                else:
                    # client: send action to host and wait for authoritative update
                    client_send_action(r,c)

            # check pop locally only on host
            # (pop is already handled inside apply_click when necessary)

    # status display
    status = 'Host' if is_host else 'Client'
    conn_text = 'Connected' if connected else 'Not connected'
    info = font.render(f'{status} | ID: {my_id} | {conn_text} | Turn: {turn}', True, (255,255,255))
    window.blit(info, (10, HEIGHT - 40))

    pg.display.update()
    clock.tick(60)

# cleanup
try:
    if net_sock:
        net_sock.close()
except:
    pass
pg.quit()
