import inspect
import os
import random
import sys

from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

from spacecraft.server import ClientBase

def get_bots_by_name():
    source_dir, myfile = os.path.split(__file__)
    sys.path.append(os.path.join(os.getcwd(), source_dir))
    bots = {}
    for sfile in os.listdir(source_dir):
        if sfile.endswith("pyc"):
            continue
        head, tail = os.path.split(sfile)
        if myfile == tail:
            continue
        module = __import__(os.path.splitext(tail)[0])
        for name, value in inspect.getmembers(module):
            if name == "ClientBase":
                continue
            elif getattr(value, 'name', None) is not None and \
               inspect.isclass(value):
                bots[value.name] = value()
    return bots


class BorgClient(ClientBase):
    name = 'borg'

    def __init__(self):
        self.bots = get_bots_by_name()
        self.enemy = None
        self.current = None

    def messageReceived(self, message):
        if self.enemy is not None:
            self.enemy.messageReceived(message)
            return

        enemy = self.set_enemy(message)
        if enemy is not None:
            self.enemy.messageReceived(message)
            return

        self.current.messageReceived(message)

    def set_enemy(self, message):
        enemy = None
        if message.get('proximity', []):
            name = message['proximity'][0].get('name')
            if name is not None:
                enemy = self.bots.get(name)
                if enemy is not None:
                    #print 'ASSIMILATED', enemy.name
                    self.enemy = enemy
                    self.enemy.transport = self.transport
                    return self.enemy

        self.current = random.choice(self.bots.values())
        self.current.transport = self.transport
        #print 'EMULATING', self.current.name


def main():
    factory = ClientFactory()
    factory.protocol = BorgClient
    reactor.connectTCP('localhost', 11106, factory)

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
