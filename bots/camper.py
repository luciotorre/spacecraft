from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random
from spacecraft.client_helpers import relative_angle


import spacecraft
from spacecraft import euclid


class RandomClient(spacecraft.server.ClientBase):

    name = "camper"
    camp = euclid.Point2(4, 4)
    lookout = euclid.Point2(50, 50)

    def look_to(self, target):
        turn = relative_angle(self.pos.x, self.pos.y,
            target.x, target.y, self.angle)
        self.command('turn', value=turn)

    def messageReceived(self, message):
        if message.get('type') == 'sensor':
            self.pos = euclid.Point2(*message['gps']['position'])
            self.angle = message['gps']['angle']

            # if not camped goto camp position
            dist = abs(self.pos - self.camp)
            if dist > 10:
                self.look_to(self.camp)
                self.command("throttle", value=1)
            elif dist > 11:
                self.look_to(self.camp)
                self.command("throttle", value=0.1)
            else:
                 # in position
                enemy_found = False

                for obj in message.get('proximity', []):
                    if obj['object_type'] in ['player']:
                        enemy_found = True
                        enemy_pos = euclid.Point2(*obj['position'])
                        enemy_vel = euclid.Point2(*obj['velocity'])

                # if enemy nearby, aim and shoot
                if enemy_found:
                    self.look_to(enemy_pos)
                    self.command("fire")
                else:
                    # else just aim to lookout
                    self.look_to(self.lookout)
                    self.command("fire")


def main():
    factory = ClientFactory()
    factory.protocol = RandomClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
