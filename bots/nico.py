from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random

import spacecraft


class NicoClient(spacecraft.server.ClientBase):
    name = 'nico bot'
    def messageReceived(self, message):
        self.command("throttle", value=1)
        self.command("fire")
        if random() < 0.2:
            self.command("turn", value=1)

def main():
    factory = ClientFactory()
    factory.protocol = NicoClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
