from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import shuffle, choice
from spacecraft.client_helpers import relative_angle
from spacecraft.euclid import LineSegment2, Point2, Matrix3
from math import sqrt, atan2, pi

import spacecraft
TILE_SIZE = 10
TWO_PI = 2 * pi

def dist(x1, y1, x2, y2):
    return sqrt((x1 - x2)**2 + (y1 - y2)**2)

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
        return self.intersect(other) is not None

    def intersect(self, other):
        return self.segment.intersect(other)


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


class Guesstimate(object):
    def __init__(self, x, y, speedx, speedy):
        self.x, self.y, self.speedx, self.speedy = x, y, speedx, speedy
        self.certainty = 50

    def step(self):
        self.x += self.speedx / 10
        self.y += self.speedy / 10
        self.certainty -= 1

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
        self.guesstimate = None

    def messageReceived(self, message):
        parser = getattr(self, 'parse_' + message.get('type', ''), None)
        if parser:
            parser(message)

    def filter_visible(self, objs, x, y, obj_type):
        result = [o for o in objs if o['object_type'] == obj_type and
                self.has_line_of_fire(x, y, o['position'][0], o['position'][1])]
        result.sort(key=lambda o:(o['position'][0] - x)**2 + (o['position'][1] - y)**2)
        return result

    def is_incoming(self, x, y, bullet):
        bulletx, bullety = bullet['position']
        speedx, speedy = bullet['velocity']
        nextdist = dist(x, y, bulletx + speedx, bullety + speedy)
        return nextdist < dist(x, y, bulletx, bullety) * 0.9

    def parse_sensor(self, message):
        if 'gps' not in message:
            return
        x, y = message['gps']['position']
        angle = message['gps']['angle']
        speedx, speedy = message['gps']['velocity']
        # Increase visited tile count
        self.visit(x, y)

        objs = message.get('proximity', [])
        bullets = self.filter_visible(objs, x, y, 'bullet')
        bullets = [b for b in bullets if self.is_incoming(x, y, b)]
        players = self.filter_visible(objs, x, y, 'player')
        powerups = self.filter_visible(objs, x, y, 'powerup')
        if players:
            #~ print "Firing at player"
            obj = players[0]
            trackx, tracky = obj['position']
            trackspeedx, trackspeedy = obj['velocity']
            d = dist(x, y, trackx, tracky)
            turn = relative_angle(x, y, trackx, tracky, angle)
            self.command('turn', value=turn)
            self.guesstimate = Guesstimate(trackx, tracky, trackspeedx, trackspeedy)
            self.command("fire")
        elif bullets:
            #~ print "Firing at bullet"
            obj = bullets[0]
            trackx, tracky = obj['position']
            trackspeedx, trackspeedy = obj['velocity']
            d = sqrt((x - trackx)**2 + (y - tracky)**2)
            turn = relative_angle(x, y, trackx, tracky, angle)
            self.command('turn', value=turn)
            self.command("fire")
        elif powerups:
            #~ print "Grabbing powerup"
            obj = powerups[0]
            trackx, tracky = obj['position']
            trackspeedx, trackspeedy = obj['velocity']
            d = sqrt((x - trackx)**2 + (y - tracky)**2)
            # (x + speedx, y + speedy) here, to compensate the "orbit" effect
            turn = relative_angle(
                x + speedx * d / 70, y + speedy * d / 70,
                trackx, tracky, angle)
            self.command('turn', value=turn)
            self.command("throttle", value=1)
            #~ else:
                #~ print obj
        elif self.guesstimate and self.guesstimate.certainty > 0:
            #~ print "Firing at a guesstimate", self.guesstimate.certainty
            turn = relative_angle(x, y, self.guesstimate.x, self.guesstimate.y, angle)
            self.command('turn', value=turn)
            self.command("fire")
            self.guesstimate.step()
        else:
            #~ print "No guesstimate"
            # Pick a good next exploration tile
            if self.going is None or not self.has_line_of_fire(x, y, self.going.x, self.going.y):
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
            speed = speedx**2 + speedy**2
            speedangle = atan2(speedy, speedx)
            targetangle = atan2(self.going.y - y, self.going.x - x)
            #~ print speed, angle, speedangle
            divergence = (targetangle - speedangle) % TWO_PI
            divergence = min(divergence, TWO_PI - divergence)
            if speed > 500 and divergence < 0.1:
                #~ print "Firing at random"
                fireangle = self.pick_fireangle(x, y, speedx, speedy, angle)
                if fireangle is not None:
                    self.command("turn", value=fireangle)
                    if abs(fireangle) < 1:
                        self.command('fire')  # Take that!
            else:
                #~ if speed <= 1590:
                    #~ print "Not bang because speed = %.3f" % speed
                #~ elif divergence >= 0.1:
                    #~ print "Not bang because divergence = %.3f" % divergence
                #~ else:
                    #~ print "EH!? OGG WANT BANG!!1! Y U NO BANG!??!?1!?"
                #~ print "Going to", self.going
                turn = relative_angle(x, y, self.going.x + speedx, self.going.y + speedy, angle)
                self.command("throttle", value=1)
                self.command("turn", value=turn)

    def has_line_of_fire(self, x, y, trackx, tracky):
        segment = LineSegment2(Point2(x, y), Point2(trackx, tracky))
        for wall in self.walls:
            if wall.blocks(segment):
                return False
        return True

    def parse_map_description(self, message):
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
        #~ print "At", visited
        visited.visits += 1
        if visited == self.going:
            self.going = None

    def pick_fireangle(self, x, y, speedx, speedy, angle):
        origin = Point2(x, y)
        delta = Point2(speedx, speedy)
        leftangle = Matrix3.new_rotate(pi / 2)
        rightangle = Matrix3.new_rotate(-pi / 2)
        targetleft = origin + leftangle * delta * 100
        targetright = origin + rightangle * delta * 100
        left = LineSegment2(origin, targetleft)
        right = LineSegment2(origin, targetright)
        dleft = dright = 10000000
        for w in self.walls:
            ileft = w.intersect(left)
            if ileft:
                dleft = min(dleft, ileft.distance(origin))
            iright = w.intersect(right)
            if iright:
                dright = min(dright, iright.distance(origin))
        if max(dleft, dright) < 35:
            return
        COMPENSATE = pi / 8
        if dleft > dright:
            targetleft = Matrix3.new_rotate(COMPENSATE) * targetleft
            result = relative_angle(x, y, targetleft.x, targetleft.y, angle)
        else:
            targetright = Matrix3.new_rotate(-COMPENSATE) * targetright
            result = relative_angle(x, y, targetright.x, targetright.y, angle)
        return result

def main():
    factory = ClientFactory()
    factory.protocol = NavigatorClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
