import numpy as np

from time import time


class Ball:
    def __init__(self, position: np.array, velocity: np.array, bounds: np.array, radius):
        self.position = position
        self.velocity = velocity

        # A 2d list of shape (2,2) giving min and max values of x and y. Ex:[[0.,1280.],[0., # 720.]]
        self.bounds = bounds

        # Units = pixels
        self.radius = radius

    def update_pos(self, dt):
        self.position += self.velocity * dt

    def bound_check(self, index):
        # index = 0 is for x axis, index = 1 is for y axis
        if self.position[index] + self.radius > self.bounds[index][1]:
            self.position[index] = self.bounds[index][1] - self.radius
        elif self.position[index] - self.radius < self.bounds[index][0]:
            self.position[index] = self.bounds[index][0] + self.radius
        else:
            return False
        self.velocity[index] *= -1
        return True

    def velocity_magnitude(self):
        return np.sqrt(np.dot(self.velocity, self.velocity))


class Paddle:
    def __init__(self, extreme_points: np.array, width: float, paddle_speed: float, ball_spawn_point: np.array):

        # The range where the ends of the paddle can be.
        self.start_point = extreme_points[0]
        self.end_point = extreme_points[1]

        # Coordinate of middle point of paddle. Ranges from 0 to 1.
        self._coordinate = 0.5

        # Speed of coordinate in coordinate units not pixels.
        self.speed = paddle_speed

        # Width is a number between 0 and 1.
        # Scales down the distance between the start and end point to get width in pixels.
        self.width = width

        self.bound_dir_ratio: np.array = self.end_point - self.start_point

        # Scale down the bound direction ratio to get the direction ratio of the paddle.
        self.width_dir_ratio = self.bound_dir_ratio * width

        # Paddle width in pixels
        self.paddle_width = np.sqrt(np.dot(self.width_dir_ratio, self.width_dir_ratio))

        self.dir_cosine = self.width_dir_ratio / self.paddle_width

        # The range where the midpoint of the paddle can be.
        self.mid_start_point = self.start_point + self.width_dir_ratio / 2
        self.mid_end_point = self.end_point - self.width_dir_ratio / 2

        self.dir_ratio = self.mid_end_point - self.mid_start_point

        # Scale down the direction ratio using the coordinate and add to mid_start_point
        # to get position vector of mid point of paddle with respect to origin.
        self.mid = self.mid_start_point + self.dir_ratio * self.coordinate

        # Get the end points of the paddle.
        self.paddle_points = self.mid - self.width_dir_ratio / 2, self.mid + self.width_dir_ratio / 2

        # Get the normal by rotating dir_cosine by 90deg
        # and checking whether it points towards the spawn point of the ball
        self.normal = np.matmul(np.array([[0., -1.], [1., 0.]]), self.dir_cosine)
        if np.dot(ball_spawn_point - self.mid, self.normal) < 0:
            self.normal *= -1

    def update(self, direction, dt):
        self.coordinate += self.speed * direction * dt

    @property
    def coordinate(self):
        return self._coordinate

    @coordinate.setter
    def coordinate(self, value):
        self._coordinate = value
        # Update midpoint and paddle points
        self.mid = self.mid_start_point + self.dir_ratio * self.coordinate
        self.paddle_points = self.mid - self.width_dir_ratio / 2, self.mid + self.width_dir_ratio / 2

    def bound_check(self):
        """Makes sure coordinate is in between 0 and 1"""
        self.coordinate = min(max(0, self.coordinate), 1)

    def do_collision(self, ball: Ball, speed_multiplier=1.):
        # ONLY WORKS FOR BALLS WITH SMALL RADII.

        # Check whether the ball is intersecting the paddle or has passed through the line containing the paddle.
        if not self.check_side(ball.position, ball.radius):
            return True, False

        # Find the intersection point of the incident path and the line containing the paddle.
        a1, a2 = self.paddle_points[0]
        b1, b2 = self.dir_ratio
        A1, A2 = ball.position
        B1, B2 = ball.velocity
        p1 = a2 * b1 - a1 * b2
        p2 = A2 * B1 - A1 * B2
        p3 = B2 * b1 - b2 * B1
        p = np.array([B1 * p1 - b1 * p2, B2 * p1 - b2 * p2]) / p3

        # Check whether the intersection point lies on the paddle.
        if np.dot(p - self.paddle_points[0], p - self.paddle_points[1]) > 0:
            # Paddle does not touch the ball.
            return False, False

        # Get the position of center of ball when the ball just touches the paddle.
        touch_point = p + ball.radius * ball.velocity / np.dot(ball.velocity, self.normal)

        # Get the return velocity direction.
        s = touch_point - self.paddle_points[0]
        t = 2 * (np.sqrt(np.dot(s, s)) / self.paddle_width - 0.5)
        return_velocity = (self.normal + t * self.dir_cosine)

        # adjust the speed.
        return_velocity *= ball.velocity_magnitude() * speed_multiplier / np.sqrt(
            np.dot(return_velocity, return_velocity))
        ball.position = touch_point
        ball.velocity = return_velocity
        return True, True

    def get_sqr_perp_dist(self, ball_pos):
        # Dist formula in vector form d = (a-c) + (b.(a-c))b
        # a = point on line, c = point not on line, b = direction cosine.
        a_minus_c = self.mid - ball_pos
        d = a_minus_c + np.dot(self.dir_cosine, a_minus_c) * self.dir_cosine
        return np.dot(d, d)

    def check_side(self, ball_pos, ball_radius):
        if np.dot(ball_pos - self.mid, self.normal) > 0:
            return False
        return self.get_sqr_perp_dist(ball_pos) > ball_radius ** 2


def get_random_dir():
    angle = np.pi * (1 - np.random.normal(0.5))
    angle *= 1 if np.random.randint(1) else -1
    return np.array([np.cos(angle), np.sin(angle)])


def get_ball_velocity():
    ball_dir = get_random_dir() * ball_speed_normalized
    return np.array([ball_dir[0] * W, ball_dir[1] * H])


if __name__ == "__main__":
    import pygame
    from pygame.locals import *

    pygame.init()
    Resolution = W, H = 1280, 720
    Fullscreen = True

    if Fullscreen:
        screen = pygame.display.set_mode(Resolution, FULLSCREEN)
    else:
        screen = pygame.display.set_mode(Resolution)
    ball_speed_normalized = 0.3

    my_ball_1 = Ball(np.array(Resolution, dtype="float64") / 2, get_ball_velocity(),
                     np.array([[0., W], [0., H]], dtype="float64"), 3)
    offset = W / 10

    my_paddle_1 = Paddle(np.array([[0 + offset, 0], [0 + offset, H]], dtype="float64"), 0.1, 1, my_ball_1.position)

    my_paddle_2 = Paddle(np.array([[W - offset, 0], [W - offset, H]], dtype="float64"), 0.1, 1, my_ball_1.position)

    running = 1

    speed_multiplier = 1.05

    fps = 240
    sec_per_frame = 1 / fps

    start = time()
    point_time = False
    player_1 = player_2 = 0
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = 0
            if event.type == KEYUP:
                if event.key == K_ESCAPE:
                    running = 0

        keys = pygame.key.get_pressed()

        if keys[K_w] and not keys[K_s]:
            direction_1 = -1
        elif keys[K_s] and not keys[K_w]:
            direction_1 = 1
        else:
            direction_1 = 0

        if keys[K_UP] and not keys[K_DOWN]:
            direction_2 = -1
        elif keys[K_DOWN] and not keys[K_UP]:
            direction_2 = 1
        else:
            direction_2 = 0

        screen.fill((120, 120, 120))
        pygame.draw.circle(screen, (255, 255, 255), my_ball_1.position,
                           my_ball_1.radius)
        pygame.draw.line(screen, (255, 255, 255), *my_paddle_1.paddle_points)
        pygame.draw.line(screen, (255, 255, 255), *my_paddle_2.paddle_points)
        pygame.display.flip()

        now = time()
        dt = now - start

        my_ball_1.update_pos(dt)
        if point_time:
            if my_ball_1.bound_check(0):
                point_time = False
                my_ball_1.position = np.array(Resolution) / 2
                my_ball_1.velocity = get_ball_velocity()
                print(f"{player_1}:{player_2}")
        my_ball_1.bound_check(1)

        if direction_1:
            my_paddle_1.update(direction_1, dt)
            my_paddle_1.bound_check()

        if direction_2:
            my_paddle_2.update(direction_2, dt)
            my_paddle_2.bound_check()
        if not point_time:
            if not my_paddle_1.do_collision(my_ball_1, speed_multiplier)[0]:
                point_time = True
                player_2 += 1
            if not my_paddle_2.do_collision(my_ball_1, speed_multiplier)[0]:
                point_time = True
                player_1 += 1

        while time() - start < sec_per_frame:
            pass
        start = now

    pygame.quit()
    print(f"{player_1}:{player_2}")
