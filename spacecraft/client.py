# -*- coding: utf-8 *-*
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

import spacecraft


class Client(spacecraft.server.ClientBase):
    def connectionLost(self, reason):
        reactor.stop()

    def command(self, msg_type, **kwargs):
        kwargs["type"] = msg_type
        self.sendMessage(kwargs)


class SampleClient(Client):

    def messageReceived(self, message):
        print message
        self.command("throttle", value=1)
        self.command("turn", value=-1)
        self.command("fire")

    def connectionMade(self):
        self.command("throttle", value=1)


class SampleClientFactory(ClientFactory):
    protocol = SampleClient

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()


def main():
    reactor.connectTCP("localhost", 11106, SampleClientFactory())


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
