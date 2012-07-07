import math

from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random
from spacecraft.client_helpers import relative_angle


import spacecraft

class BFClient(spacecraft.server.ClientBase):
    name = 'Ali'
    def messageReceived(self, message):
        if message['type'] == 'sensor' and message.get('gps', False):
            gps = message['gps']
            x, y = message['gps']['position']
            angle = message['gps']['angle']
            fire = 0

            # Butterfly
            if far_from_center(gps):
                if looking_center(gps):
                    throttle = 1
                else:
                    throttle = 0
                turn = relative_angle(x, y, 50, 50, angle)
            else:
                turn = 1
                fire = 1
                if random() < 0.3:
                    throttle = 1
                else:
                    throttle = 0

            # Speed control
            if too_fast(gps) and not looking_center(gps):
                throttle = 0

            if too_slow(gps):
                throttle = 1

            # Lock-on
            closer_player = get_closer_player(message)
            if closer_player and closer_player['distance'] < 50:
                px, py = closer_player['position']
                turn = relative_angle(x, y, px, py, angle)
                if should_fire(closer_player, turn):
                    fire = 1
                else:
                    fire = 0

            if point_defense(message):
                print "PD"
                fire = 1

            self.command("throttle", value=throttle)
            self.command("turn", value=turn)
            if fire:
                self.command("fire")


def looking_center(gps):
    x, y = gps['position']
    angle = gps['angle']
    return math.fabs(relative_angle(x, y, 50, 50, angle)) < 5


def far_from_center(gps):
    x, y = gps['position']
    d = 10
    return math.fabs(x-50) > d or math.fabs(y-50) > d


def too_fast(gps):
    vx, vy = gps['velocity']
    return math.fabs(vx) + math.fabs(vy) > 15


def too_slow(gps):
    vx, vy = gps['velocity']
    return math.fabs(vx) + math.fabs(vy) < 7


def get_closer_player(message):
    myxy = message['gps']['position']
    players = []
    for obj in message.get('proximity', []):
        if obj['object_type'] in ['player']:
            pxy = obj['position']
            players.append({'position': obj['position'],
                            'distance': distance(myxy, pxy)})
    if players:
        return sorted(players, key=get_distance)[0]
    else:
        return {}


def get_distance(p):
    return p['distance']


def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)


def should_fire(player, relative_angle):
    return player['distance'] < 30 and math.fabs(relative_angle) < 2


def point_defense(message):
    myxy = message['gps']['position']
    angle = message['gps']['angle']
    for obj in message.get('proximity', []):
        if obj['object_type'] in ['bullet']:
            pxy = obj['position']
            d = distance(myxy, pxy)
            a = relative_angle(myxy[0], myxy[1], pxy[0], pxy[1], angle)
            if d < 2 and a < 2:
                return True
    return False


def main():
    factory = ClientFactory()
    factory.protocol = BFClient
    reactor.connectTCP("localhost", 11106, factory)


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
