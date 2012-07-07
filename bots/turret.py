# -*- coding: utf-8 *-*
import random
from bunch import bunchify
from math import pi

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from spacecraft.server import ClientBase
from spacecraft.euclid import Point2, Vector2
from spacecraft.client_helpers import relative_angle

AIM = 0.2
POS_PER_VEL = 0.1

class TurretBotClient(ClientBase):
    name = 'Turret'

    def messageReceived(self, msg):
        msg = bunchify(msg)

        if 'status' in msg:
            targets = [obj for obj in msg.proximity
                       if obj.object_type == 'player']

            if targets:
                my_pos= Point2(*msg.gps.position)

                # aim and shoot target
                t = targets[0]
                t_pos = Point2(t.position[0] + t.velocity[0] * POS_PER_VEL,
                               t.position[1] + t.velocity[1] * POS_PER_VEL)

                turn = relative_angle(my_pos.x, my_pos.y,
                                      t_pos.x, t_pos.y,
                                      msg.gps.angle)

                self.command('turn', value=turn)
                self.command('fire')

            else:
                self.command('turn', value=0.1)
                self.command('fire')

        else:
            #print msg
            pass



def main():
    factory = ClientFactory()
    factory.protocol = TurretBotClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
