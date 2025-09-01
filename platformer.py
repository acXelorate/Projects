import pygame as pg
pg.init()
pg.mixer.init()
pg.font.init()
window=pg.display.set_mode((800,800))

font=pg.font.SysFont(None,50)
winfont=pg.font.SysFont(None,200)

room=1

timer=0

version=1.0

rcolor=(56, 125, 235)
pcolor=(27, 97, 209)
gcolor=(18, 81, 181)
fcolor=(4, 38, 92)

plist=[]
plist.append(pg.Rect(0,700,800,100)) #floor
plist.append(pg.Rect(0,0,800,1))     #ceiling

splist=[]
splist.append(0)
splist.append(0)
splist.append(0)
splist.append(0)
splist.append(0)
splist.append(0)
splist.append(0)


plist.append(pg.Rect(400,550,100,50))
plist.append(pg.Rect(100,400,200,50))
plist.append(pg.Rect(0,250,100,50))
plist.append(pg.Rect(200,100,400,50))
plist.append(pg.Rect(700,250,100,50))

elist=[]
elist.append(pg.Rect(200,390,50,10))
elist.append(pg.Rect(300,90,30,10))
elist.append(pg.Rect(500,90,30,10))

ulist=[]

e2list=[]

door=pg.Rect(750,150,50,100)

def recolor(roomcolor,playercolor,platformcolor,fontcolor):
    
    global rcolor
    global gcolor
    global pcolor
    global fcolor
    rcolor=roomcolor
    gcolor=playercolor
    pcolor=platformcolor
    fcolor=fontcolor

class Pp:
    def __init__(self,Rect):
        self.Rect=Rect
        self.Gravity=0
    def draw(self):
        pg.draw.rect(window,gcolor,self.Rect)
    def move(self,dist):
        if pg.Rect(self.Rect.x+dist,self.Rect.y,50,50).collidelist(plist)==-1:
            if not self.Rect.x+dist<=0:
                if not self.Rect.x+dist>=750:
                    self.Rect.x+=dist
                else:
                    self.Rect.x=750
            else:
                self.Rect.x=0

    def jump(self):
        if pg.Rect(self.Rect.x,self.Rect.y+1,50,50).collidelist(plist)!=-1:
            if self.Gravity<=0:
                self.Gravity=30
    def grav(self):
        if self.Gravity>0:
            if pg.Rect(self.Rect.x,self.Rect.y-self.Gravity/3,50,50).collidelist(plist)==-1:
                self.Rect.y-=self.Gravity/3
                self.Gravity-=1
            else:
                while pg.Rect(self.Rect.x,self.Rect.y-1,50,50).collidelist(plist)==-1:
                    self.Rect.y-=1
                self.Gravity=0
        elif self.Rect.collidelist(ulist)!=-1:
            self.Gravity=0
        elif pg.Rect(self.Rect.x,self.Rect.y+1,50,50).collidelist(plist)==-1:
            self.Gravity-=1
            self.Rect.y-=self.Gravity/3

        else:
            self.Gravity=0
    def collidecheck(self):
        while self.Rect.collidelist(plist)!=-1:
            self.Rect.y-=1
    def kill(self):
        if self.Rect.collidelist(elist)!=-1:
            self.Rect=pg.Rect(50,650,50,50)
    def up(self):
        if self.Rect.collidelist(ulist)!=-1:
            
            if pg.Rect(self.Rect.x,self.Rect.y-5,50,50).collidelist(plist)==-1:
                self.Rect.y-=5
                
    def nextroom(self):
        global room
        global door
        if self.Rect.colliderect(door) or u:
            self.Rect=pg.Rect(50,650,50,50)
            plist.clear()
            elist.clear()
            ulist.clear()
            splist.clear()
            plist.append(pg.Rect(0,700,800,100)) #floor
            plist.append(pg.Rect(0,0,800,1))
            
            room+=1
            if room==2:
                door=pg.Rect(100,175,50,100)
                     #ceiling

                plist.append(pg.Rect(200,600,100,50))
                plist.append(pg.Rect(250,550,50,50))
                plist.append(pg.Rect(350,500,50,50))
                plist.append(pg.Rect(250,350,50,50))
                plist.append(pg.Rect(575,350,50,50))
                plist.append(pg.Rect(750,250,50,50))
                plist.append(pg.Rect(650,100,50,50))
                plist.append(pg.Rect(600,150,50,50))
                plist.append(pg.Rect(500,75,50,50))
                plist.append(pg.Rect(350,75,50,50))
                plist.append(pg.Rect(200,75,50,50))
                plist.append(pg.Rect(155,175,50,100))
                plist.append(pg.Rect(45,175,50,100))
                plist.append(pg.Rect(45,275,160,50))

                for i in range(len(plist)):
                    splist.append(0)

                elist.append(pg.Rect(250,500,50,50))
                elist.append(pg.Rect(400,349,175,50))

                recolor((51, 232, 57),(21, 89, 24),(38, 148, 43),(14, 89, 17))

            if room==3:
                door=pg.Rect(0,100,50,100)

                ulist.append(pg.Rect(200,400,100,300))
                ulist.append(pg.Rect(400,200,100,200))
                ulist.append(pg.Rect(750,200,50,200))

                elist.append(pg.Rect(400,150,100,50))
                elist.append(pg.Rect(600,350,50,50))

                plist.append(pg.Rect(300,400,500,50))
                plist.append(pg.Rect(0,400,200,50))
                plist.append(pg.Rect(0,200,400,50))
                plist.append(pg.Rect(600,200,150,50))

                for i in range(len(plist)):
                    splist.append(0)

                recolor((214, 51, 211),(143, 20, 141),(173, 33, 171),(84, 21, 83))

            if room==4:
                door=pg.Rect(750,0,50,100)

                elist.append(pg.Rect(200,650,175,50))
                elist.append(pg.Rect(500,650,175,50))
                elist.append(pg.Rect(200,350,175,50))
                elist.append(pg.Rect(500,350,175,50))

                ulist.append(pg.Rect(750,400,50,300))
                ulist.append(pg.Rect(0,100,50,300))

                plist.append(pg.Rect(0,400,750,50))
                plist.append(pg.Rect(50,100,750,50))

                for i in range(len(plist)):
                    splist.append(0)

                recolor((221, 255, 69),(162, 184, 68),(151, 181, 16),(108, 128, 23))

            if room==5:
                door=pg.Rect(750,600,50,100)

                ulist.append(pg.Rect(0,0,50,700))

                plist.append(pg.Rect(100,55,50,650))
                plist.append(pg.Rect(50,55,350,50))

                for i in range(len(plist)):
                    splist.append(0)

                elist.append(pg.Rect(380,300,200,50))
                elist.append(pg.Rect(580,500,200,50))
                elist.append(pg.Rect(310,500,200,50))

                recolor((158,158,158),(64, 64, 64),(99, 99, 99),(43, 43, 43))

            if room==6:
                door=pg.Rect(750,600,50,100)

                plist.append(pg.Rect(100,100,50,50))
                
                plist.append(pg.Rect(250,0,50,50))
                
                plist.append(pg.Rect(400,-100,50,50))
                
                plist.append(pg.Rect(550,-200,50,50))
                
                for i in range(len(plist)):
                    splist.append(0)

                splist[0+2]=1
                splist[1+2]=1
                splist[2+2]=1
                splist[3+2]=1

                elist.append(pg.Rect(100,675,600,25))

                recolor((56, 125, 235),(27, 97, 209),(18, 81, 181),(4, 38, 92))

            if room==7:

                door=pg.Rect(750,0,50,100)

                ulist.append(pg.Rect(0,50,100,650))

                plist.append(pg.Rect(250,0,50,50))
                plist.append(pg.Rect(350,-150,50,50))
                plist.append(pg.Rect(450,-300,50,50))
                plist.append(pg.Rect(550,-450,50,50))
                plist.append(pg.Rect(650,-600,50,50))
                plist.append(pg.Rect(100,75,50,750))

                elist.append(pg.Rect(150,675,650,25))                

                for i in range(len(plist)):
                    splist.append(0)

                splist[0+2]=1
                splist[1+2]=1
                splist[2+2]=1
                splist[3+2]=1
                splist[4+2]=1
                
                recolor((51, 232, 57),(21, 89, 24),(38, 148, 43),(14, 89, 17))

            if room==8:
                door=pg.Rect(750,0,50,100)

                plist.append(pg.Rect(0,100,50,50))
                plist.append(pg.Rect(0,200,50,50))
                plist.append(pg.Rect(0,300,50,50))
                plist.append(pg.Rect(0,400,50,50))
                plist.append(pg.Rect(0,500,50,50))
                plist.append(pg.Rect(0,600,50,50))
                
                

                for i in range(len(plist)):
                    splist.append(0)

                splist[0+2]=2
                splist[1+2]=3
                splist[2+2]=2
                splist[3+2]=3
                splist[4+2]=2
                splist[5+2]=3

                recolor((214, 51, 211),(143, 20, 141),(173, 33, 171),(84, 21, 83))

            if room==9:
                door=pg.Rect(750,0,50,100)

                plist.append(pg.Rect(100,0,50,50)) #down
                plist.append(pg.Rect(100,800,50,50)) #up

                plist.append(pg.Rect(300,0,50,50)) #down
                plist.append(pg.Rect(300,800,50,50)) #up

                plist.append(pg.Rect(500,0,50,50)) #down
                plist.append(pg.Rect(500,800,50,50)) #up

                plist.append(pg.Rect(700,0,50,50)) #down
                plist.append(pg.Rect(700,800,50,50)) #up


                plist.append(pg.Rect(0,100,50,50))#right
                plist.append(pg.Rect(800,100,50,50))#left

                plist.append(pg.Rect(0,300,50,50))#right
                plist.append(pg.Rect(800,300,50,50))#left

                plist.append(pg.Rect(0,500,50,50))#right
                plist.append(pg.Rect(800,500,50,50))#left

                plist.append(pg.Rect(0,700,50,50))#right
                plist.append(pg.Rect(800,700,50,50))#left

                for i in range(len(plist)):
                    splist.append(0)

                splist[0+2]=1
                splist[1+2]=4
                splist[2+2]=1
                splist[3+2]=4
                splist[4+2]=1
                splist[5+2]=4
                splist[6+2]=1
                splist[7+2]=4

                splist[8+2]=2
                splist[9+2]=3
                splist[10+2]=2
                splist[11+2]=3
                splist[12+2]=2
                splist[13+2]=3
                splist[14+2]=2
                splist[15+2]=3
                

                recolor((221, 255, 69),(162, 184, 68),(151, 181, 16),(108, 128, 23))

            if room==10:
                door=pg.Rect(375,0,50,100)
                plist.append(pg.Rect(0,500,100,50))
                plist.append(pg.Rect(800,500,100,50))
                plist.append(pg.Rect(300,300,100,50))
                plist.append(pg.Rect(700,300,100,50))
                plist.append(pg.Rect(400,500,100,50))
                plist.append(pg.Rect(500,500,100,50))
                plist.append(pg.Rect(150,300,100,50))
                plist.append(pg.Rect(300,300,100,50))
                plist.append(pg.Rect(500,100,100,50))
                plist.append(pg.Rect(800,100,100,50))
                plist.append(pg.Rect(100,100,100,50))
                plist.append(pg.Rect(400,100,100,50))


                for i in range(5):
                    for rect in range(3):
                        elist.append(pg.Rect(i*200,rect*300,50,50))
                

                plist.append(pg.Rect(325,100,150,50))
                plist.append(pg.Rect(325,650,150,50))
                for i in range(len(plist)):
                    splist.append(0)
                splist[0+2]=2
                splist[1+2]=3
                splist[2+2]=2
                splist[3+2]=3
                splist[4+2]=2
                splist[5+2]=3
                splist[6+2]=2
                splist[7+2]=3
                splist[8+2]=2
                splist[9+2]=3
                splist[10+2]=2
                splist[11+2]=3

                recolor((158,158,158),(64, 64, 64),(99, 99, 99),(43, 43, 43))


Player=Pp(pg.Rect(50,650,50,50))

while True:
    u=0
    for event in pg.event.get():
        if event.type==pg.QUIT:
            quit()
        elif event.type==pg.KEYDOWN:
            if event.key==pg.K_SPACE or event.key==pg.K_w or event.key==pg.K_UP:
                Player.jump()
            if event.key==pg.K_0:
                u=1
    keys=pg.key.get_pressed()
    if keys[pg.K_d] or keys[pg.K_RIGHT]:
        Player.move(5)
    if keys[pg.K_a] or keys[pg.K_LEFT]:
        Player.move(-5)
    if room!=11:
        timer+=16

    

    Player.grav()

    Player.collidecheck()

    Player.kill()

    Player.up()

    Player.nextroom()

    window.fill(rcolor)

    for o in range(len(plist)):
        i=plist[o]
        if splist:
            spec=splist[o]
        else:
            spec=0
        if spec==1:
            if not Player.Rect.colliderect(pg.Rect(i.x,i.y-1,i.width,i.height)):
                i.y+=2
                if i.y>=800:
                    i.y=0
        if spec==2:
            i.x+=2
            if i.x>=800:
                i.x=-50
        if spec==3:
            i.x-=2
            if i.x<=-50:
                i.x=800
        if spec==4:
            if not Player.Rect.colliderect(pg.Rect(i.x,i.y-1,i.width,i.height)):
                i.y-=2
                if i.y<=-50:
                    i.y=800
        pg.draw.rect(window,pcolor,i)
        
    for i in elist:
        pg.draw.rect(window,"red",i)
    for i in ulist:
        pg.draw.rect(window,"yellow",i)
    
    pg.draw.rect(window,"brown",door)

    Player.draw()

    txt=font.render(f"ROOM:{room}",True,fcolor)
    window.blit(txt,(0,700))
    txt=font.render(f"TIMER:{round((timer/1000),2)}",True,fcolor)
    window.blit(txt,(200,700))

    if room==11:
        window.fill("black")
        txt=winfont.render("YOU WIN",True,"white")
        window.blit(txt,(0,0))
        txt=font.render(f"time:{round((timer/1000),2)}",True,"white")
        window.blit(txt,(0,700))

    pg.display.update()
    pg.time.wait(16)