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

#LOCATIONS = [ # for basic map
#    complex(10,10),
#    complex(10,90),
#    complex(90,10),
#    complex(90,90)
#]
LOCATIONS = [ # for cross.svg
       complex(10, 300-280),
       complex(275, 300-280),
       complex(270, 300-10),
       complex(95, 300-10),
       complex(270, 300-60),
       complex(230, 300-60),
       complex(230, 300-180),
       complex(110, 300-180),
       complex(150, 300-115),
       complex(170, 300-55),
       complex(52, 300-27),
       complex(12, 300-12),
       complex(34, 300-145),
       complex(77, 300-205),
       complex(145, 300-240),
       complex(246, 300-265),
       complex(94, 300-108),
]

NEAR_DISTANCE = 5 # To arrive to a checkpoint
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
            "position": [-1, -1],
            "velocity": [0, 0],
            "angle": 0,
        }
        self.dest = complex(-1, -1)
        self.target_id = None
        self.map = []

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

    def line_of_sight(self,point):
        """
        Returns true iff there is line of sight to given point, considering
        map walls. Assumes nonwrapping/closed map
        """
        from spacecraft import euclid
        ray = euclid.LineSegment2(
            euclid.Point2(self.location.real, self.location.imag),
            euclid.Point2(point.real, point.imag),
        )
        #print "Checking", len(self.map), "walls;", F(self.location), F(point)
        for w in self.map:
            corners = [
                euclid.Point2(w['x'], w['y']),
                euclid.Point2(w['x']+w['width'], w['y']),
                euclid.Point2(w['x'], w['y']+w['height']),
                euclid.Point2(w['x']+w['width'], w['y']+w['height']),
            ]
            sides = [
                euclid.LineSegment2(corners[0], corners[1]),
                euclid.LineSegment2(corners[0], corners[2]),
                euclid.LineSegment2(corners[3], corners[1]),
                euclid.LineSegment2(corners[3], corners[2]),
            ]
            for s in sides:
                if ray.intersect(s):
                    return False
        return True

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
        if self.location.real < 0: # Game hasn't started, do nothing
            return
        # powerup?
        for item in self.proximity:
            if item["object_type"] == "powerup":
                d = complex(*item["position"])
                if self.line_of_sight(d):
                    self.dest = d
                    break
        # Pick a destination, far away, but reachable
        while abs(self.location - self.dest) < NEAR_DISTANCE or not self.line_of_sight(self.dest):
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
            if nrel_v.real*nrel_p.real + nrel_v.imag*nrel_p.imag > 0.1 and (abs(rel_v)>4 or abs(rel_p) > 6):
                self.command("throttle", value=ATTACK_THRUST)
        self.aim(location-self.location)

    def backtrack_shots(self):
        """
        Check bullets that don't appear to have been originated from us.
        calculate some interesection points and average them to extrapolate
        enemy position. Aim there and fire.
        """
        from spacecraft.euclid import Point2, Vector2, Circle, Ray2
        me = Circle(Point2(self.location.real, self.location.imag), 5.0)
        enemy_shots = []
        for item in self.proximity:
            if item["object_type"] == "bullet":
                ray = Ray2(
                    Point2(*item["position"]),
                    -Vector2(*item["velocity"])
                )
                if not ray.intersect(me): # assume enemy shot
                    enemy_shots.append(ray)

        if not enemy_shots: return False # no enemy shots seen
        if len(enemy_shots)==1:
            enemy = enemy_shots[0]
            enemy_position = enemy.p + enemy.v*35 # Assume right outside sensor range
            target = complex(enemy_position.x, enemy_position.y)
        else:
            pts = []
            for i,v in enumerate(enemy_shots[:-1]):
                estimate = v.intersect(enemy_shots[i+1])
                if estimate:
                    pts.append(estimate)
            if not pts: return False # no data to estimate
            x = sum(p.x for p in pts)/len(pts)
            y = sum(p.y for p in pts)/len(pts)
            target = complex(x, y)

        self.aim(target-self.location)
        self.command("throttle", value=ATTACK_THRUST)
        self.shoot()
        return True
            


    def check_enemies(self):
        """Choose if attack, defend or patrol"""
        for item in self.proximity:
            if item["object_type"] == "player":
                self.target_id = item["id"]
                if self.line_of_sight(complex(*item["position"])):
                    self.attack(item)
                    break
        else:
            # No enemy found, backtrack shots, or patrol around
            if not self.backtrack_shots():
                self.target_id = None
                self.patrol()

    def messageReceived(self, message):
        mtype = message["type"]
        if mtype == "time":
            self.time = message["step"]
        elif mtype == "map_description":
            self.map = message["terrain"]
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
