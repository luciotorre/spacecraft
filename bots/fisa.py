# -*- coding: utf-8 *-*
from bunch import bunchify
import random
import cmath

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from spacecraft.server import ClientBase
from spacecraft.euclid import Point2, Vector2
from spacecraft.client_helpers import relative_angle

AIM = 0.2

SEARCH_THROTTLE = 0.5
SEARCH_THROTTLES = 20
SEARCH_TURNS = 3
MAX_SPEED = 15
WALL_SAFE_DISTANCE = 20


class FisaBotClient(ClientBase):
    name = 'Fisa'

    def __init__(self):
        self.throttles_left = 0
        self.turns_left = 0
        self.turn = 0

    def point_and_shoot(self, target):
        # where to aim
        vel_modifier = 1
        if target.object_type == 'player':
            vel_modifier = 0.1
        elif target.object_type == 'bullet':
            vel_modifier = 0.2
        aim_at = predict_pos(target.position, target.velocity, vel_modifier)

        turn = relative_angle(self.pos.x, self.pos.y,
                              aim_at.x, aim_at.y,
                              self.angle)
        # aim and shoot
        self.command('turn', value=turn)
        self.command('fire')

    def wall_between(self, position):
        for wall_side in self.wall_sides:
            if intersect(self.pos, position,
                         wall_side[0], wall_side[1]):
                return True
        return False


    def messageReceived(self, msg):
        msg = bunchify(msg)

        if msg.type == 'sensor':
            # useful data transformations
            self.pos = Point2(*msg.gps.position)
            self.vel = Vector2(*msg.gps.velocity)
            self.angle = msg.gps.angle

            radar = [obj for obj in msg.proximity]
            for x in radar:
                x.position = Point2(*x.position)
                x.velocity = Vector2(*x.velocity)

            # find enemies
            enemies = [obj for obj in radar
                       if obj.object_type == 'player' and \
                          not self.wall_between(obj.position)]

            if enemies:
                # pick closest
                e = sorted([(self.pos.distance(e.position), e)
                            for e in enemies])[0][1]

                # shoot the enemy
                self.point_and_shoot(e)

            else:
                # find bullets
                bullets = [obj for obj in radar
                           if obj.object_type == 'bullet']
                incoming = []
                # calculate incoming
                for b in bullets:
                    future_b_pos = predict_pos(b.position, b.velocity, 0.1)
                    future_my_pos = predict_pos(self.pos, self.vel, 0.1)
                    distance = self.pos.distance(b.position)
                    future_distance = future_my_pos.distance(future_b_pos)
                    if distance > future_distance:
                        incoming.append((future_distance - distance, b))

                if incoming:
                    # pick the bullet that's closing faster
                    b = sorted(incoming)[0][1]

                    # point and shoot the bullet
                    self.point_and_shoot(b)
                else:
                    # move N times, then rotate N times
                    # will hit wall?
                    pointing_vector = cmath.rect(WALL_SAFE_DISTANCE, self.angle)
                    pointing_vector = Vector2(pointing_vector.real, pointing_vector.imag)
                    pointing_to = predict_pos(self.pos, pointing_vector)
                    wall_in_front = self.wall_between(pointing_to)

                    if self.throttles_left:
                        # must move
                        if wall_in_front:
                            # but made half movements and still not velocity
                            # so stop, turn, and try again
                            self.throttles_left = 0
                            self.turn = 1
                            self.turns_left = 0
                            self.command('turn', value=1)
                        else:
                            # keep moving
                            self.throttles_left -= 1
                            if abs(self.vel.x) + abs(self.vel.y) < MAX_SPEED:
                                # but no accelerate too much
                                self.command('throttle', value=SEARCH_THROTTLE)

                    elif self.turns_left:
                        # must rotate
                        self.turns_left -= 1
                        self.command('turn', value=self.turn)
                    else:
                        # finish moving and rotating, start again
                        self.throttles_left = SEARCH_THROTTLES
                        self.turns_left = SEARCH_TURNS
                        self.turn = random.randint(-1, 1)

                    if not wall_in_front:
                        self.command('fire')

        elif msg.type == 'map_description':
            self.terrain = msg.terrain
            self.wall_sides = []
            for wall in self.terrain:
                x, y = wall.x, wall.y
                x2, y2 = wall.x + wall.width, wall.y + wall.height
                self.wall_sides.append((Point2(x, y), Point2(x2, y)))
                self.wall_sides.append((Point2(x, y), Point2(x, y2)))
                self.wall_sides.append((Point2(x2, y), Point2(x2, y2)))
                self.wall_sides.append((Point2(x, y2), Point2(x, y2)))


def predict_pos(point, velocity, modifier=1):
    v = velocity
    if modifier != 1:
        v = Vector2(velocity.x * modifier,
                    velocity.y * modifier)
    return point + v


def ccw(a,b,c):
    return (c[1]-a[1])*(b[0]-a[0]) > (b[1]-a[1])*(c[0]-a[0])

def intersect(a,b,c,d):
    return ccw(a,c,d) != ccw(b,c,d) and ccw(a,b,c) != ccw(a,b,d)


def main():
    factory = ClientFactory()
    factory.protocol = FisaBotClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
