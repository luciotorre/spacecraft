# -*- coding: utf-8 *-*
import uuid
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
import random
from spacecraft.client_helpers import relative_angle
import maptools

import spacecraft
from spacecraft import euclid
p2 =  euclid.Point2


def closer(target, candidates):
    ranked = [(abs(target - p), p) for p in candidates]
    ranked.sort()
    return ranked[0][1]


class RandomClient(spacecraft.server.ClientBase):

    name = "ckr_" + str(uuid.uuid4())[:3]

    gridmap = None
    way = None
    waypoints = [
        p2(20, 280),
        p2(180, 240),
        p2(240, 210),
        p2(195, 60),
        p2(81, 90),
        p2(110, 286),
        p2(286, 38),
        ]

    def look_to(self, target):
        turn = relative_angle(self.pos.x, self.pos.y,
            target.x, target.y, self.angle)
        self.command('turn', value=turn)

    def goto(self, target):
        if abs(self.vel) > 10:
            target = target - self.vel
        else:
            target = target
        self.look_to(target)

    def aim(self, target, target_velocity):
        dist = abs(self.pos - target)
        target = target + target_velocity * dist / 70
        self.look_to(target)

    def messageReceived(self, message):
        if self.gridmap is None:
            self.gridmap = maptools.GridMap("maps/cross.svg")
            self.way = random.choice(self.waypoints)
            self.gridmap.set_goal(self.way)

        if message.get('type') == 'sensor':
            if not "gps" in message:
                return

            self.pos = euclid.Point2(*message['gps']['position'])
            self.vel = euclid.Point2(*message['gps']['velocity'])
            self.angle = message['gps']['angle']
            self.health = message['status']['health']
            # if number of enemies visible == 1
            # rush!
            enemies = 0
            pp = None

            for obj in message.get('proximity', []):
                if obj['object_type'] in ['player']:
                    enemies += 1
                    ep = p2(*obj['position'])
                    ev = p2(*obj['velocity'])
                if obj['object_type'] in ['powerup']:
                    pp = p2(*obj['position'])

            if enemies == 1 and self.health > 100:
                if self.gridmap.visible(self.pos, ep):
                    self.aim(ep, ev)
                    self.command("throttle", value=1)
                    self.command("fire")
                    return
                else:
                    print "enemy not visible."
            elif enemies > 1:
                # FLEE
                while abs(self.pos - self.camp) < 150:
                    self.way = random.choice(self.waypoints)
                    self.gridmap.set_goal(self.way)

            if pp is not None and enemies == 0:
                # a powerup!!!
                print "poweeeeeeeeeeeeer"
                if self.gridmap.visible(self.pos, pp):
                    self.goto(pp)
                    self.command("throttle", value=1)
                    if self.way != pp:
                        print "set way to pp"
                        self.way = pp
                        self.gridmap.set_goal(self.way)
                    return
                else:
                    print "not visible, way to pp", pp
                    if self.way != pp:
                        self.way = pp
                        self.gridmap.set_goal(self.way)

            # go towards waypoint
            if abs(self.pos - self.way) < 10:
                # select new way we havent visited in a while
                self.way = random.choice(self.waypoints)
                self.gridmap.set_goal(self.way)

            self.waypoint = p2(*self.gridmap.towards_goal_from(self.pos))


            self.goto(self.waypoint)
            self.command("throttle", value=1)



def main():
    factory = ClientFactory()
    factory.protocol = RandomClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
