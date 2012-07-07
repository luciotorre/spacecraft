from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from random import random

import spacecraft


class HelicopterClient(spacecraft.server.ClientBase):
    name = 'helicopter'
    def messageReceived(self, message):
        self.command("fire")
        if random() < 0.6:
            self.command("turn", value=1)

def main():
    factory = ClientFactory()
    factory.protocol = HelicopterClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
