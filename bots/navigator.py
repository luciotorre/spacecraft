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

    name = "navigator_" + str(uuid.uuid4())[:3]

    gridmap = None
    way = None
    target = None
    waypoints = [
        p2(10, 10),
        p2(290, 10),
        p2(10, 290),
        p2(290, 290)
        ]

    camp = p2(96, 295)
    camplook = [p2(284, 273)]

    camp_options = [
            (p2(96, 295), [p2(284, 273)]),
            (p2(294, 7), [p2(292, 77), p2(14, 22)])

        ]

    def look_to(self, target):
        turn = relative_angle(self.pos.x, self.pos.y,
            target.x, target.y, self.angle)
        self.command('turn', value=turn)

    def goto(self, target):
        dist = abs(self.pos - target)
        target = target - self.vel * dist / 70
        self.look_to(target)

    def aim(self, target, target_velocity):
        dist = abs(self.pos - target)
        target = target + target_velocity * dist / 70
        self.look_to(target)

    def messageReceived(self, message):
        if self.gridmap is None:
            self.gridmap = maptools.GridMap("maps/cross.svg")
            self.camp, self.camp_look = random.choice(self.camp_options)
            self.gridmap.set_goal(self.camp)

        if message.get('type') == 'sensor':
            if not "gps" in message:
                return

            self.pos = euclid.Point2(*message['gps']['position'])
            self.vel = euclid.Point2(*message['gps']['velocity'])
            self.angle = message['gps']['angle']

            # if number of enemies visible == 1
            # rush!
            enemies = 0

            for obj in message.get('proximity', []):
                if obj['object_type'] in ['player']:
                    enemies += 1
                    ep = p2(*obj['position'])
                    ev = p2(*obj['velocity'])

            if enemies == 1:
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
                    self.camp, self.camp_look = random.choice(self.camp_options)


            # camped!!!
            if abs(self.pos - self.camp) < 10:
                #print "camped"
                self.look_to(random.choice(self.camp_look))
                self.command('fire')

                # get bored, change position
                if random.random() < 0.005:
                    self.camp, self.camp_look = random.choice(self.camp_options)
                    self.gridmap.set_goal(self.camp)
                return

            # over wall!!! wander
            if not self.gridmap.is_wall(self.pos):
                print "walled, wandering"
                self.command("throttle", value=1)
                if random.random() < 0.2:
                    self.command("turn", value=1)
                return


            waypoint = p2(*self.gridmap.towards_goal_from(self.pos))

            self.goto(waypoint)
            self.command("throttle", value=1)



def main():
    factory = ClientFactory()
    factory.protocol = RandomClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
