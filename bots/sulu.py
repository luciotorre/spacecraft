from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import shuffle, choice
from spacecraft.client_helpers import relative_angle
from spacecraft.euclid import LineSegment2, Point2
from math import sqrt, atan2, pi

import spacecraft
TILE_SIZE = 10
INITIAL_FOCUS = 50
TWO_PI = 2 * pi
HALF_A_DEGREE = pi / 360

class Wall(object):
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        if w > h:
            yavg = y + h / 2
            self.segment = LineSegment2(Point2(x, yavg), Point2(x + w, yavg))
        else:
            xavg = x + w / 2
            self.segment = LineSegment2(Point2(xavg, y), Point2(xavg, y + h))

    def blocks(self, other):
        result = self.segment.intersect(other)
        return result is not None

class Tile(object):
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.visits = 0

    def has_wall(self, wall):
        return (self.x1 <= wall.x + wall.w and self.x2 >= wall.x and
                self.y1 <= wall.y + wall.h and self.y2 >= wall.y)

    @property
    def x1(self):
        return self.x - self.size / 2
    @property
    def x2(self):
        return self.x + self.size / 2
    @property
    def y1(self):
        return self.y - self.size / 2
    @property
    def y2(self):
        return self.y + self.size / 2

    def distance_to(self, x, y):
        return (self.x - x) ** 2 + (self.y - y) ** 2

    def __str__(self):
        return "Tile(%s, %s)" % (self.x, self.y)

    __repr__ = __str__


class NavigatorClient(spacecraft.server.ClientBase):
    @property
    def name(self):
        adjectives = ['better', 'improved', 'wonderful', 'pretty', 'assertive',
            'neat']
        return '%s navigator' % choice(adjectives)

    def __init__(self):
        self.tiles = []
        self.walls = []
        self.going = None
        self.focus = 0

    def messageReceived(self, message):
        #~ print message
        if message.get('type') == 'sensor':
            if 'gps' not in message:
                return
            self.command("throttle", value=1)
            x, y = message['gps']['position']
            angle = message['gps']['angle']
            speedx, speedy = message['gps']['velocity']
            tracking = False
            # Increase visited tile count
            self.visit(x, y)

            # Check if we should track
            for obj in message.get('proximity', []):
                if obj['object_type'] in ['powerup', 'player']:
                    trackx, tracky = obj['position']
                    trackspeedx, trackspeedy = obj['velocity']
                    if self.has_line_of_fire(x, y, trackx, tracky):
                        tracking = True
                        d = sqrt((x - trackx)**2 + (y - tracky)**2)
                        # (x + speedx, y + speedy) here, to compensate the "orbit" effect
                        turn = relative_angle(
                            x + speedx * d / 70, y + speedy * d / 70,
                            trackx, tracky, angle)
                        self.command('turn', value=turn)
                        if obj['object_type'] == 'player':
                            self.command("fire")
                    break
            if not tracking:
                # Pick a good next exploration tile
                if (self.going is None or self.focus <= 0 or
                    not self.has_line_of_fire(x, y, self.going.x, self.going.y)):
                    options = [t for t in self.tiles
                                if self.has_line_of_fire(x, y, t.x, t.y)]
                    if not options:
                        return
                    options.sort(key=lambda x: x.visits)
                    options = [o for o in options if o.visits == options[0].visits]
                    #~ print "Options:", options
                    self.going = max(options, key=lambda t:t.distance_to(x, y))
                    # Random exploration
                    #~ shuffle(options)
                    #~ self.going = min(options, key=lambda t:t.visits)
                    self.focus = INITIAL_FOCUS
                print "Going to: %s, focus=%s" % (self.going, self.focus)
                
                turn = relative_angle(x, y, self.going.x + speedx, self.going.y + speedy, angle)
                speed = speedx**2 + speedy**2
                speedangle = atan2(speedy, speedx) % TWO_PI
                #~ self.focus -= 1
                print turn, speed, angle, speedangle
                if abs(turn) < 0.005 and speed > 1590 and abs(angle - speedangle) < HALF_A_DEGREE:
                    print "bang!"
                else:
                    self.command("turn", value=turn)
        elif message.get('type') == 'map_description':
            self.parse_terrain(message)

    def has_line_of_fire(self, x, y, trackx, tracky):
        segment = LineSegment2(Point2(x, y), Point2(trackx, tracky))
        for wall in self.walls:
            if wall.blocks(segment):
                return False
        return True

    def parse_terrain(self, message):
        for wall in message['terrain']:
            if wall['type'] != 'wall':
                continue
            wobject = Wall(wall['x'], wall['y'], wall['width'], wall['height'])
            self.walls.append(wobject)

        xsize = message.get('xsize', 100) / TILE_SIZE
        ysize = message.get('ysize', 100) / TILE_SIZE
        for x in range(xsize):
            for y in range(ysize):
                ts = TILE_SIZE
                tile = Tile(x * ts + ts / 2, y * ts + ts / 2, ts)
                self.tiles.append(tile)
                add = True
                for w in self.walls:
                    if tile.has_wall(w):
                        add = False
                        break
                if add:
                    self.tiles.append(tile)

    def visit(self, x, y):
        visited = min(self.tiles, key=lambda t:t.distance_to(x, y))
        print "At", visited
        visited.visits += 1
        if visited == self.going:
            self.going = None

def main():
    factory = ClientFactory()
    factory.protocol = NavigatorClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
