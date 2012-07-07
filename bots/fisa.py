# -*- coding: utf-8 *-*
from bunch import bunchify
import random

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from spacecraft.server import ClientBase
from spacecraft.euclid import Point2
from spacecraft.client_helpers import relative_angle

AIM = 0.2
POS_PER_VEL = 0.1

SEARCH_THROTTLE = 0.3
SEARCH_THROTTLES = 20
SEARCH_TURNS = 3

class FisaBotClient(ClientBase):
    name = 'Fisa'

    def __init__(self):
        self.throttles_left = 0
        self.turns_left = 0
        self.turn = 0

    def messageReceived(self, msg):
        msg = bunchify(msg)

        if msg.type == 'sensor':
            targets = [obj for obj in msg.proximity
                       if obj.object_type == 'player']

            if targets:
                my_pos= Point2(*msg.gps.position)
                # rotate aiming to the target
                t = targets[0]
                t_pos = Point2(t.position[0] + t.velocity[0] * POS_PER_VEL,
                               t.position[1] + t.velocity[1] * POS_PER_VEL)

                turn = relative_angle(my_pos.x, my_pos.y,
                                      t_pos.x, t_pos.y,
                                      msg.gps.angle)

                # do the rotation and shoot
                self.command('turn', value=turn)
                self.command('fire')

            else:
                # rotate a tick and move N times
                if self.throttles_left:
                    self.throttles_left -= 1
                    self.command('throttle', value=SEARCH_THROTTLE)
                elif self.turns_left:
                    self.turns_left -= 1
                    self.command('turn', value=self.turn)
                else:
                    self.throttles_left = SEARCH_THROTTLES
                    self.turns_left = SEARCH_TURNS
                    self.turn = random.randint(-1, 1)

                if abs(msg.gps.velocity[0]) + abs(msg.gps.velocity[1]) > 0.05:
                    # shoot if not hitting a wall
                    self.command('fire')


        elif msg.type == 'map_description':
            self.terrain = msg.terrain


def main():
    factory = ClientFactory()
    factory.protocol = FisaBotClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
