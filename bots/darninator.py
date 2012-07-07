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
    complex(10,10),
    complex(10,90),
    complex(90,10),
    complex(90,90)
]
NEAR_DISTANCE = 10
TURN_EPSILON = 0.01 # If cos(angle to destination) < this, don't bother to turn
AHEAD = 0.6 # If cos(angle to target) < this, fire
VELOCITY_COMPENSATE = 1.0
ENEMY_PREDICT = 0.2 # aim prediction for enemy
VERY_HURT = 0 # If less than this, bee defensive
TOO_CLOSE = 8 # IF enemy is at less of this distance, dodge

TURN_SPEED = math.pi / 8

def normalize(v):
    return v/abs(v)

def F(c):
    return "(%.2f, %.2f)" % (c.real, c.imag)

class DarniClient(ClientBase):

    name = "darninator"

    def __init__(self):
        self.time = -1
        self.health = 100
        self.proximity = []
        self.old_proximity = []
        self.gps = {
            "position": [0, 0],
            "velocity": [0, 0],
            "angle": 0,
        }
        self.mode = None
        self.dest = complex(0, 0)
        self.target_id = None

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
        # Find where I should aim at
        target = (self.dest-self.location) - VELOCITY_COMPENSATE*self.velocity # Vector to target + compensation for velocity
        direction = normalize(target/self.angle)
        if abs(direction.imag) > TURN_EPSILON or direction.real < 0: # we need to turn
            # Compute how much. approximately
            angle = min(direction.imag / math.sin(TURN_SPEED), 1)
            self.command("turn", value=angle)
        self.command("throttle", value=0.5)

    def attack(self, item):
        #print "(attack)"
        # position, compensated with fudge factor and relative velocity
        location = complex(*item["position"]) + ENEMY_PREDICT*(complex(*item["velocity"]) - self.velocity)
        rel_angle = normalize(location - self.location) / self.angle
        # if it's sort of ahead.... fire
        if rel_angle.real > 0  and abs(rel_angle.imag) < AHEAD:
            self.command("fire")
            rel_v = complex(*item["velocity"]) - self.velocity
            rel_p = complex(*item["position"]) - self.location
            # if it's getting away, chase
            if rel_v.real*rel_p.real + rel_v.imag*rel_p.imag < 0:
                self.command("thrust", value=0.5)
        # aim
        angle = min(rel_angle.imag / math.sin(TURN_SPEED), 1)
        self.command("turn", value=angle)

    def defend(self, item):
        enemy_angle = normalize(complex(*item["position"])-self.location)
        desired_angle = enemy_angle * 1j
        direction = desired_angle / self.angle
        if abs(direction) > TURN_EPSILON or direction.real < 0: # we need to turn
            # Compute how much. approximately
            angle = min(direction.imag / math.sin(TURN_SPEED), 1)
            self.command("turn", value=angle)
        self.command("throttle", value=1)

    def attack_or_defend(self, item):
        """
        Decide if for given enemy, it's convenient to attack or defend
        
        returns self.defend or self.attack accordingly
        """
        location = complex(*item["position"])
        rel_location = location - self.location
        
        if abs(rel_location) < TOO_CLOSE:
            return self.defend
        if self.health < VERY_HURT: # Defensive strategy
            rel_location = normalize(rel_location)
            enemy_angle = item["angle"]
            enemy_angle = math.cos(enemy_angle) +1j*math.sin(enemy_angle)
            # make enemy_angle relative to current orientation towards enemy
            enemy_angle /= rel_location
            if enemy_angle.real < 0 and abs(enemy_angle.imag) < AHEAD:
                return self.defend
            else:
                return self.attack
        else:
            return self.attack

    def check_enemies(self):
        """Choose if attack, defend or patrol"""
        for item in self.proximity:
            if item["object_type"] == "player":
                self.target_id = item["id"]
                action = self.attack_or_defend(item)
                action(item)
                break
        else:
            # No enemy found, patrol for more
            self.target_id = None
            self.patrol()

    def messageReceived(self, message):
        mtype = message["type"]
        if self.mode is None:
            self.patrol()
        if mtype == "time":
            self.time = message["step"]
        elif mtype == "sensor":
            self.health = message["status"]["health"]
            self.gps = message["gps"]
            self.old_proximity = self.proximity
            self.proximity = message["proximity"]
        else:
            print message
        self.check_enemies()

#            self.command("turn", value=1) # LEFT
#            self.command("turn", value=-1) # RIGHT
#            self.command("throttle", value=1)
#            self.command("fire")

class DarniClientFactory(ClientFactory):
    protocol = DarniClient


def main():
    reactor.connectTCP("localhost", 11106, DarniClientFactory())


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
