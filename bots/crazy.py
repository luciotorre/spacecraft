# -*- coding: utf-8 *-*
from random import randint, random
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

import spacecraft
from spacecraft.client_helpers import relative_angle


class Crazy(spacecraft.server.ClientBase):
    name = "crazy"

    def follow(self, my_position, enemy_position, my_angle):
        angle_relat = relative_angle(my_position[0],
                                     my_position[1],
                                     enemy_position[0],
                                     enemy_position[1],
                                     my_angle)
        self.command("turn", value=angle_relat)

    def messageReceived(self, msg):
        if msg["type"] == "sensor":
            enemy = False
            powerup = False
            my_position = msg.get("gps", {}).get("position", [0, 0])
            my_angle = msg.get("gps", {}).get("angle", 0.0)
            for proximity in msg.get("proximity", []):
                if proximity["object_type"] == "player":
                    enemy = True
                elif proximity["object_type"] == "powerup":
                    powerup = True
            for proximity in msg.get("proximity", []):
                if proximity["object_type"] == "player":
                    enemy_position = proximity["position"]
                    self.follow(my_position, enemy_position, my_angle)
                    self.command("fire")
                    self.command("throttle", value=1.0)
                    break
                elif proximity["object_type"] == "powerup" and not enemy:
                    powerup_position = proximity["position"]
                    self.command("throttle", value=0.9)
                    self.follow(my_position, powerup_position, my_angle)
                elif not enemy and not powerup:
                    self.command("turn", value=0.1)
                    self.command("throttle", value=1.0)
                    self.command("fire")


def main():
    factory = ClientFactory()
    factory.protocol = Crazy
    reactor.connectTCP("localhost", 11106, factory)


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
