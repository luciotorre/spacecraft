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
                # shoot closest target
                my_pos= Point2(*msg.gps.position)

                # pick closest
                t = sorted([(my_pos.distance(Point2(*t.position)), t)
                            for t in targets])[0][1]
                # where to aim
                aim_at = Point2(t.position[0] + t.velocity[0] * POS_PER_VEL,
                                t.position[1] + t.velocity[1] * POS_PER_VEL)
                turn = relative_angle(my_pos.x, my_pos.y,
                                      aim_at.x, aim_at.y,
                                      msg.gps.angle)

                # aim and shoot
                self.command('turn', value=turn)
                self.command('fire')

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
