from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
import random
from spacecraft.client_helpers import relative_angle


import spacecraft
from spacecraft import euclid


def closer(target, candidates):
    ranked = [(abs(target - p), p) for p in candidates]
    ranked.sort()
    return ranked[0][1]


class RandomClient(spacecraft.server.ClientBase):

    name = "camper"
    camp = None
    lookout = euclid.Point2(50, 50)
    lookout_duration = 1

    path = []
    old = [
        euclid.Point2(15.404826, 14.010764),
        euclid.Point2(79.549515, 17.167492),
        euclid.Point2(84.600273, 88.00444),

    ]

    camp_positions = [
        euclid.Point2(4, 4),
        euclid.Point2(95, 95),
        euclid.Point2(4, 95),
        euclid.Point2(95, 4)
        ]

    lookout_positions = [
        euclid.Point2(40, 60),
        euclid.Point2(60, 40),
        euclid.Point2(60, 60),
        euclid.Point2(40, 40),
        ]

    def goto(self, target):
        # aim to corrected goal
        # if more or less looking
        # throttle
        pass

    def look_to(self, target):
        turn = relative_angle(self.pos.x, self.pos.y,
            target.x, target.y, self.angle)
        self.command('turn', value=turn)

    def messageReceived(self, message):
        if message.get('type') == 'sensor':
            if not "gps" in message:
                return

            self.pos = euclid.Point2(*message['gps']['position'])
            self.angle = message['gps']['angle']

            enemy_found = False

            for obj in message.get('proximity', []):
                if obj['object_type'] in ['player']:
                    enemy_found = True
                    enemy_pos = euclid.Point2(*obj['position'])
                    enemy_vel = euclid.Point2(*obj['velocity'])

            # if enemy nearby, aim and shoot
            if enemy_found:
                #self.camp = random.choice(self.camp_positions)
                self.look_to(enemy_pos)
                self.command("throttle", value=0.1)
                self.command("fire")
                return

            if not self.camp:
                # pick closest
                self.camp = closer(self.pos, self.camp_positions)

            if self.path:
                dist = abs(self.pos - self.path[0])
                if dist > 3:
                    self.look_to(self.path[0])
                    self.command("throttle", value=1)
                else:
                    self.path = self.path[1:]
                return


            # if not camped goto camp position
            print self.camp
            dist = abs(self.pos - self.camp)
            if dist > 10:
                self.look_to(self.camp)
                self.command("throttle", value=1)
            elif dist > 11:
                self.look_to(self.camp)
                self.command("throttle", value=0.1)
            else:
                 # in position
                # else just aim to lookout
                self.look_to(self.lookout)
                self.command("fire")
                if self.lookout_duration < 0.5:
                    self.lookout = random.choice(self.lookout_positions)
                    self.lookout_duration = 1
                self.lookout_duration -= 0.05


def main():
    factory = ClientFactory()
    factory.protocol = RandomClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
