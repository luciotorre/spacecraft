# -*- coding: utf-8 *-*
from bunch import bunchify
import random

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from spacecraft.server import ClientBase
from spacecraft.euclid import Point2, Vector2
from spacecraft.client_helpers import relative_angle

AIM = 0.2

SEARCH_THROTTLE = 0.3
SEARCH_THROTTLES = 20
SEARCH_TURNS = 3
SPEED_PREDICTION_RATIO = 0.01

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

        aim_at = Point2(target.position.x + target.velocity.x * vel_modifier,
                        target.position.y + target.velocity.y * vel_modifier)
        turn = relative_angle(self.pos.x, self.pos.y,
                              aim_at.x, aim_at.y,
                              self.angle)
        # aim and shoot
        self.command('turn', value=turn)
        self.command('fire')

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
                       if obj.object_type == 'player']

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
                    future_b_pos = b.position + b.velocity
                    future_my_pos = self.pos + self.vel
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
                    if self.throttles_left:
                        # must move
                        if self.throttles_left < SEARCH_THROTTLES / 2 and \
                           not is_moving(msg.gps.velocity):
                               # but made half movements and still not velocity
                               # so stop throttling and turn back
                               self.throttles_left = 0
                               self.turn = 1
                               self.turns_left = 5
                               self.command('turn', value=1)
                        else:
                            # keep moving
                            self.throttles_left -= 1
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

                    if is_moving(msg.gps.velocity):
                        # shoot if not hitting a wall
                        self.command('fire')


        elif msg.type == 'map_description':
            self.terrain = msg.terrain


def is_moving(velocity):
    return abs(velocity[0]) + abs(velocity[1]) > 0.1


def main():
    factory = ClientFactory()
    factory.protocol = FisaBotClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
