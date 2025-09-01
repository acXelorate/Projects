import pygame as pg
from random import randint

turn=randint(1,2)

redfirst=1    #red/blue first turn (setting up the 3 pointer)
bluefirst=1

pg.init()
pg.font.init()
window=pg.display.set_mode((800,800))
pg.display.set_caption("COLOR WARS")

font=pg.font.SysFont(None,250)

rectlist=[]



tempx=0
tempy=0
for i in range(25):
    rectlist.append(pg.Rect(tempx,tempy,160,160))
    tempx+=160
    if tempx>=800:
        tempx=0
        tempy+=160
rectlist = [rectlist[i:i+5] for i in range(0, len(rectlist), 5)]

board=[[0,0,0,0,0],
       [0,0,0,0,0],
       [0,0,0,0,0],
       [0,0,0,0,0],
       [0,0,0,0,0],]

owner=[[0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],]

def pop(own):
    global board
    global owner
    global row
    global col
    try:
        if row-1!=-1:
            board[row-1][col]+=1
    except:
        pass
    try:
        board[row+1][col]+=1
    except:
        pass
    try:
        if col-1!=-1:
            board[row][col-1]+=1
    except:
        pass
    try:
        board[row][col+1]+=1
    except:
        pass
    try:
        if row-1!=-1:    
            owner[row-1][col]=own
    except:
        pass
    try:
        owner[row+1][col]=own
    except:
        pass
    try:
        if col-1!=-1:
            owner[row][col-1]=own
    except:
        pass
    try:
        owner[row][col+1]=own    
    except:
        pass

while True:
    mousex,mousey=pg.mouse.get_pos()
    leftclick=0
    for event in pg.event.get():
        if event.type==pg.QUIT:
            quit()
        elif event.type==pg.MOUSEBUTTONDOWN:
            if event.button==1:
                leftclick=1
    if turn==2:
        window.fill("red")
    else:
        window.fill("blue")
    
    for row in range(5):
        for col in range(5):
            rect=rectlist[row][col]
            val=board[row][col]
            own=owner[row][col]
            pg.draw.rect(window, "black", rect,1)
            if own==1:
                txt=font.render(str(val),True,(0,0,150))
                window.blit(txt,rect)
            elif own==2:
                txt=font.render(str(val),True,(150,0,0))
                window.blit(txt,rect)
            if turn==1:
                if bluefirst and rect.collidepoint(mousex,mousey) and leftclick and val==0:
                    leftclick=0
                    own=1
                    val=3
                    turn=2
                    bluefirst=0

                if rect.collidepoint(mousex,mousey) and leftclick and own==1:
                    leftclick=0
                    val+=1
                    turn=2
                    

            if turn==2:
                if redfirst and rect.collidepoint(mousex,mousey) and leftclick and val==0:
                    leftclick=0
                    own=2
                    val=3
                    turn=1
                    redfirst=0

                if rect.collidepoint(mousex,mousey) and leftclick and own==2:
                    leftclick=0
                    val+=1
                    turn=1

            if val>=4:
                pop(own)
                val=0
                own=0

            board[row][col]=val
            owner[row][col]=own

    pg.time.wait(16)
    pg.display.update()