"""Purely cosmetic sparks."""

from math import pi
from random import (
    choice,
    randint,
    random,
)
from pygame import Color

from spacecraft import euclid


class Spark(object):
    def __init__(self, engine, pos, color, speed, ttl):
        self.x, self.y = pos
        self.sx, self.sy = speed
        self.color = color
        self.ttl = ttl
        self.engine = engine

    def step(self):
        self.x += self.sx
        self.y += self.sy
        self.ttl -= 1
        if self.ttl == 0:
            self.engine.remove_spark(self)
        else:
            self.draw()

    def draw(self):
        pos = int(round(self.x)), int(round(self.y))
        self.engine.screen.set_at(pos, self.color)


class SparkEngine(object):
    colors = [Color('#b80000'), Color('#b82500'), Color('#b85900'),
              Color('#b86400')]

    def __init__(self, screen):
        self.sparks = []
        self.screen = screen

    def random_color(self):
        return choice(self.colors)

    def add_spark(self, pos, angle, speed):
        color = self.random_color()
        speed = speed + (euclid.Matrix3.new_rotate(random() * pi / 3 -
            pi / 6 - angle) * euclid.Vector2(-randint(2, 8), 0))
        ttl = randint(2, 5)
        self.sparks.append(Spark(self, pos, color, speed, ttl))

    def add_burst(self, pos, angle, speed, number):
        for i in range(number):
            self.add_spark(pos, angle, speed)

    def remove_spark(self, spark):
        self.sparks.remove(spark)

    def step(self):
        for spark in self.sparks:
            spark.step()
