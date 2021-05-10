import socket
import pickle
import json
import pygame
from pygame.locals import *

pygame.init()


mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mySocket.connect((socket.gethostname(), 9000))
header_length = 64


def recv_with_header():
    msg_length = int(mySocket.recv(header_length).decode().rstrip())
    return mySocket.recv(msg_length)


res, fps, ball, my_paddle = pickle.loads(recv_with_header())
Resolution = W, H = res
screen = pygame.display.set_mode(Resolution)
other_paddles = pickle.loads(recv_with_header())

running = 1
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = 0
        if event.type == KEYUP:
            if event.key == K_ESCAPE:
                running = 0
    screen.fill((120, 120, 120))
    data = json.loads(recv_with_header().decode())
    my_paddle.coordinate = data[1]
    for paddle, coordinate in zip(other_paddles, data[2]):
        paddle.coordinate = coordinate
    pygame.draw.circle(screen, (255, 255, 255), data[0],
                       3)
    pygame.draw.line(screen, (0, 255, 0), *my_paddle.paddle_points)
    for paddle in other_paddles:
        pygame.draw.line(screen, (255, 0, 0), *paddle.paddle_points)
    keys = pygame.key.get_pressed()
    if keys[K_w] and not keys[K_s]:
        mySocket.send(b"0")
    elif keys[K_s] and not keys[K_w]:
        mySocket.send(b"2")
    else:
        mySocket.send(b"1")
    pygame.display.flip()
