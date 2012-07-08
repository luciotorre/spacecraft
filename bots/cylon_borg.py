from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

from borg import BorgClient

factory = ClientFactory()

class CylonClient(BorgClient):
    name = 'cylon borg'

    def __init__(self):
        BorgClient.__init__(self)
        self.resurrected = False

    def messageReceived(self, message):
        health = message.get('status', {}).get('health', 100)
        if health <= 0 and not self.resurrected:
            self.resurrected = True
            connect_bot()
        else:
            BorgClient.messageReceived(self, message)


def connect_bot():
    factory.protocol = CylonClient
    reactor.connectTCP('localhost', 11106, factory)

if __name__ == '__main__':
    reactor.callWhenRunning(connect_bot)
    reactor.run()
