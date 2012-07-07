# -*- coding: utf-8 *-*
import pygame
import random
import math

from twisted.internet import reactor

from spacecraft.server import ClientBase
from twisted.internet.protocol import ClientFactory

# states:
# GOING: yendo a un punto (destx, desty)
# CHASING: persiguiendo a un target target_id

LOCATIONS = [
    complex(50,10),
    complex(50,90),
]
NEAR_DISTANCE = 10
TURN_EPSILON = 0.2 # If cos(angle to destination) < this, don't bother to turn
VELOCITY_COMPENSATE = 1.0

MAX_TURN = 1
TURN_SPEED = math.pi / 4 # This should be pi/8, but pi/4 works better (less oscillation).go figure

def normalize(v):
    """Normalize vector v to ensure abs(v)==1"""
    return v/abs(v)

def clamp(value, limit):
    """clamp value in the range -limit ... +limit"""
    return max(min(value, limit), -limit)

class TargetClient(ClientBase):

    name = "target"

    def __init__(self):
        self.time = -1
        self.health = 100
        self.proximity = []
        self.gps = {
            "position": [0, 0],
            "velocity": [0, 0],
            "angle": 0,
        }
        self.mode = None
        self.dest = complex(0, 0)
        self.target_id = None

    ## Utility

    def aim(self, target):
        """Aim towards target. direction should be a vector relative to us"""
        direction = normalize(target/self.angle)
        if abs(direction.imag) > TURN_EPSILON or direction.real < 0: # we need to turn
            # Compute how much. approximately
            angle = clamp(math.atan2(direction.imag, direction.real) / TURN_SPEED, MAX_TURN)
            self.command("turn", value=angle)

    ## Access
    @property
    def location(self):
        return complex(*self.gps["position"])

    @property
    def velocity(self):
        return complex(*self.gps["velocity"])

    @property
    def angle(self):
        a = self.gps["angle"]
        return math.cos(a) + 1j*math.sin(a)

    ## Strategy

    def patrol(self):
        # Pick a destination, far away
        while abs(self.location - self.dest) < NEAR_DISTANCE:
            self.dest = random.choice (LOCATIONS)
        # Find where I should aim at = Vector to target + compensation for velocity
        target = (self.dest-self.location) - VELOCITY_COMPENSATE*self.velocity
        self.aim(target)
        self.command("throttle", value=1)


    def messageReceived(self, message):
        mtype = message["type"]
        if self.mode is None:
            self.patrol()
        if mtype == "time":
            self.time = message["step"]
        elif mtype == "sensor":
            self.health = message["status"]["health"]
            self.gps = message["gps"]
            self.proximity = message["proximity"]
        else:
            print message
        self.patrol()


class TargetClientFactory(ClientFactory):
    protocol = TargetClient


def main():
    reactor.connectTCP("localhost", 11106, TargetClientFactory())


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
