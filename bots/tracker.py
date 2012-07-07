from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random
from spacecraft.client_helpers import relative_angle


import spacecraft

class RandomClient(spacecraft.server.ClientBase):
    name = 'tracker'
    def messageReceived(self, message):
        if message.get('type') == 'sensor':
            if 'gps' not in message:
                return
            self.command("throttle", value=1)
            tracking = False
            x, y = message['gps']['position']
            angle = message['gps']['angle']
            for obj in message.get('proximity', []):
                if obj['object_type'] in ['powerup', 'player']:
                    tracking = True
                    trackx, tracky = obj['position']
                    turn = relative_angle(x, y, trackx, tracky, angle)
                    self.command('turn', value=turn)
                    if obj['object_type'] == 'player':
                        self.command("fire")
                    break
            if not tracking and random() < 0.2:
                self.command("fire")
                self.command("turn", value=1)

def main():
    factory = ClientFactory()
    factory.protocol = RandomClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
