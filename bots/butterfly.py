import math

from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random, shuffle
from spacecraft.client_helpers import relative_angle


import spacecraft

class BFClient(spacecraft.server.ClientBase):
    name = 'Ali'
    steps = 0
    directions = [[-30, -30], [0, -30], [30, -30],
                  [-30, 0],             [30, 0],
                  [-30, 30],  [0, 30],  [30, 30]]
    dx = 0
    dy = 0
    def messageReceived(self, message):
        if message['type'] == 'map_description':
            self.map = message

        if message['type'] == 'sensor' and message.get('gps', False):
            self.steps += 1
            gps = message['gps']
            x, y = message['gps']['position']
            angle = message['gps']['angle']
            fire = 0

            # Butterfly
            # turn, throttle = self.butterfly(gps)

            #turn, throttle = self.navigate(gps)

            turn, throttle = self.walk_the_park(gps)

            # Speed control
            if too_fast(gps) and not looking_center(gps):
                throttle = 0

            if too_slow(gps):
                throttle = 1

            # Lock-on
            closer_player = self.get_closer_player(message)
            if closer_player:
                px, py = closer_player['position']
                turn = relative_angle(x, y, px, py, angle)
                if should_fire(closer_player, turn):
                    fire = 1
                else:
                    fire = 0

            if point_defense(message):
                fire = 1

            self.command("throttle", value=throttle)
            self.command("turn", value=turn)
            if fire:
                self.command("fire")

    def butterfly(self, gps):
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
        return turn, throttle

    def navigate(self, gps):
        m = self.steps % 300
        if m < 100:
            turn = 1
            throttle = 0
            if random() < 0.5:
                throttle = 1
        else:
            turn = 0
            throttle = 1
        return turn, throttle

    def walk_the_park(self, gps):
        x, y = gps['position']
        angle = gps['angle']
        if self.steps % 20 == 0:
            self.dx, self.dy = self.get_new_destination(gps)
            print self.dx, self.dy
        turn = relative_angle(x, y, self.dx, self.dy, angle)
        return turn, 1

    def get_new_destination(self, gps):
        x, y = gps['position']
        angle = gps['angle']
        shuffle(self.directions)
        for d in self.directions:
            pdx, pdy = x + d[0], y + d[1]
            if not self.collides(x, y, pdx, pdy) \
                    and math.fabs(relative_angle(x, y, pdx, pdy, angle)) < 5:
                print relative_angle(x, y, pdx, pdy, angle)
                return pdx, pdy
        return 0, 0

    def collides(self, x, y, pdx, pdy):
        for w in self.get_walls():
            if intersect([x, y],[pdx, pdy], w[0], w[1]):
                return True
        return False

    def get_walls(self):
        t = self.map['terrain']
        sides = []
        for w in t:
            wx, wy = w['x'], w['y']
            w, h = w['width'], w['height']
            sides.append([[wx, wy], [wx+w, wy]])
            sides.append([[wx, wy], [wx, wy+h]])
            sides.append([[wx+w, wy], [wx+w, wy+h]])
            sides.append([[wx, wy+h], [wx, wy+h]])
        return sides

    def get_center(self):
        xsize, ysize = self.map['xsize'], self.map['ysize']
        return xsize/2, ysize/2

    def get_map_size(self):
        return self.map['xsize'], self.map['ysize']

    def get_closer_player(self, message):
        myxy = message['gps']['position']
        players = []
        for obj in message.get('proximity', []):
            pxy = obj['position']
            if obj['object_type'] in ['player'] \
                    and not self.collides(myxy[0], myxy[1], pxy[0], pxy[1]):
                players.append({'position': obj['position'],
                                'distance': distance(myxy, pxy)})
        if players:
            return sorted(players, key=get_distance)[0]
        else:
            return {}


def ccw(A,B,C):
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def intersect(A,B,C,D):
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

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




def get_distance(p):
    return p['distance']


def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)


def should_fire(player, relative_angle):
    return player['distance'] < 25 and math.fabs(relative_angle) < 1


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
