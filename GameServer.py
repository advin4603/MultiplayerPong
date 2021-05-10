import socket
from collision_test import Paddle, Ball
import numpy as np
import pickle
import pygame
import json


player_count = 2
Resolution = W, H = 400, 400
width = 0.1
paddle_speed = 1
ball_spawn = np.array(Resolution) / 2
normalized_ball_speed = 0.3
ball_bounds = np.array([[0, W], [0, H]], dtype="float64")
ball_radius = 3
fps = 60
speed_multiplier = 1.05
header_length = 64


def get_extreme_points():
    offset = W / 10
    yield np.array([[offset, 0], [offset, H]], dtype="float64")
    while True:
        yield np.array([[W - offset, 0], [W - offset, H]], dtype="float64")


def get_random_dir():
    angle = np.pi * np.random.random()
    angle *= 1 if np.random.randint(1) else -1
    return np.array([np.cos(angle), np.sin(angle)])


def get_ball_velocity():
    ball_dir = get_random_dir() * normalized_ball_speed
    return np.array([ball_dir[0] * W, ball_dir[1] * H])


class Network:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_limit = player_count
        self.connection_info = []
        self.ball = Ball(ball_spawn.copy(), get_ball_velocity(), ball_bounds.copy(), 3)
        self.points_getter = get_extreme_points()
        self.paddles = []

    def bind(self):
        self.socket.bind((self.host, self.port))
        return self

    def send_all(self, msg: bytes):
        for conn_inf in self.connection_info:
            conn_inf[0].send(msg)

    def get_header(self, msg: bytes):
        return str(len(msg)).ljust(header_length, " ").encode()

    def send_with_header(self, conn, msg: bytes):
        conn.send(self.get_header(msg) + msg)

    def send_all_with_header(self, msg: bytes):
        self.send_all(self.get_header(msg) + msg)

    def listen(self):
        # Waiting
        self.socket.listen(self.player_limit)
        for _ in range(self.player_limit):
            conn_inf = self.socket.accept()
            print(f'Connection from {conn_inf[1]} has been established')
            self.connection_info.append(conn_inf)

        # Initialize

        # - Initialize Paddles
        for conn_inf in self.connection_info:
            paddle_info = next(self.points_getter), width, paddle_speed, ball_spawn
            new_paddle = Paddle(*paddle_info)
            self.paddles.append(new_paddle)
            paddle_info_bytes = pickle.dumps([Resolution, fps, self.ball, new_paddle])
            self.send_with_header(conn_inf[0], paddle_info_bytes)

        # - Send other paddles.
        for index, conn_inf in enumerate(self.connection_info):
            self.send_with_header(conn_inf[0],
                                  pickle.dumps([self.paddles[i] for i in range(self.player_limit) if i != index]))

        # - Initialize Game Loop
        clock = pygame.time.Clock()
        collision_disabled = False

        # Game Loop

        while 1:
            # - Measure delta time.
            dt = clock.tick(fps) / 1000

            # - Send display info.
            for index, conn_inf in enumerate(self.connection_info):
                msg = json.dumps([tuple(self.ball.position), self.paddles[index].coordinate,
                                  [self.paddles[i].coordinate for i in range(self.player_limit) if
                                   i != index]]).encode()
                conn_inf[0].send(self.get_header(msg) + msg)

            # - Do ball update
            self.ball.update_pos(dt)
            self.ball.bound_check(1)
            if collision_disabled and self.ball.bound_check(0):
                self.ball.position = ball_spawn.copy()
                self.ball.velocity = get_ball_velocity()
                collision_disabled = False

            # - Get Key Strokes.
            for index, conn_inf in enumerate(self.connection_info):
                direction = int(conn_inf[0].recv(1)) - 1
                self.paddles[index].update(direction, dt)
                self.paddles[index].bound_check()

            # - Do Collisions
            if not collision_disabled:
                for paddle in self.paddles:
                    ball_in_front, paddle_hit = paddle.do_collision(self.ball, speed_multiplier)
                    if not ball_in_front:
                        collision_disabled = True
                    if paddle_hit:
                        collision_disabled = False


if __name__ == "__main__":
    Network(socket.gethostname(), 9000).bind().listen()
