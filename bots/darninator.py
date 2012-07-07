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
#    complex(25,20),
#    complex(25,90),
    complex(10,10),
    complex(10,90),
    complex(90,10),
    complex(90,90)
]
NEAR_DISTANCE = 10 # To arrive to a checkpoint
TURN_EPSILON = 0.03 # If cos(angle to destination) < this, don't bother to turn
AHEAD = 0.6 # If cos(angle to target) < this, fire
DEFENSE_AHEAD = 0.2 # If cos(angle from target) < this, dodge
VELOCITY_COMPENSATE = 1.0
ENEMY_PREDICT = 0.005 # aim prediction for enemy
PREDICT_EXPONENT = 1.5
TOO_CLOSE = 10 # IF enemy is at less of this distance, dodge
ATTACK_THRUST = 1
MAX_FIRE_SPEED = 25 # Don't shoot going faster than this

MAX_TURN = 1
TURN_SPEED = math.pi / 8

def normalize(v):
    """Normalize vector v to ensure abs(v)==1"""
    return v/abs(v)

def clamp(value, limit):
    """clamp value in the range -limit ... +limit"""
    return max(min(value, limit), -limit)

def is_out(p):
    # TODO: hardocded to map
    return p.real < 4 or p.real > 96 or p.imag < 4 or p.imag > 96

def F(c):
    """Format a complex for printout"""
    return "(%.2f, %.2f)" % (c.real, c.imag)

class DarniClient(ClientBase):

    name = "darninator"

    def __init__(self):
        self.time = -1
        self.health = 100
        self.proximity = []
        self.gps = {
            "position": [0, 0],
            "velocity": [0, 0],
            "angle": 0,
        }
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

    def shoot(self):
        if abs(self.velocity) < MAX_FIRE_SPEED: # To avoid hitting our oun bullets
            self.command("fire")

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
        self.shoot()

    def attack(self, item):
        # position, compensated with fudge factor and relative velocity
        enemy_location = complex(*item["position"])
        distance = abs(enemy_location-self.location)
        location = complex(*item["position"]) + ENEMY_PREDICT*(distance**PREDICT_EXPONENT)*(complex(*item["velocity"]) - self.velocity)
        rel_angle = normalize(location - self.location) / self.angle
        # if it's sort of ahead.... fire
        if rel_angle.real > 0  and abs(rel_angle.imag) < AHEAD:
            self.shoot()
            rel_v = complex(*item["velocity"]) - self.velocity
            rel_p = complex(*item["position"]) - self.location
            nrel_v = normalize(rel_v)
            nrel_p = normalize(rel_p)
            # if it's getting away, chase
            if nrel_v.real*nrel_p.real + nrel_v.imag*nrel_p.imag > 0.1 and abs(rel_v)>4 and abs(rel_p) > 8:
                self.command("throttle", value=ATTACK_THRUST)
        self.aim(location-self.location)

    def check_enemies(self):
        """Choose if attack, defend or patrol"""
        for item in self.proximity:
            if item["object_type"] == "player":
                self.target_id = item["id"]
                self.attack(item)
                break
        else:
            # No enemy found, patrol for more
            self.target_id = None
            self.patrol()

    def messageReceived(self, message):
        mtype = message["type"]
        if mtype == "time":
            self.time = message["step"]
        elif mtype == "sensor":
            self.health = message["status"]["health"]
            self.gps = message["gps"]
            self.proximity = message["proximity"]
        elif mtype == "game_status":
            if message["current"] == "finished":
                self.transport.loseConnection()
        else:
            print message
        self.check_enemies()


class DarniClientFactory(ClientFactory):
    protocol = DarniClient


def main():
    reactor.connectTCP("localhost", 11106, DarniClientFactory())


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
