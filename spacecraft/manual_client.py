# -*- coding: utf-8 *-*
import tty
import termios
import sys
import select

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from spacecraft.server import ClientBase

old_settings = termios.tcgetattr(sys.stdin.fileno())

class ManualClient(ClientBase):
    name = 'manual'
    def __init__(self):
        self.poller = select.poll()
        self.poller.register(0, select.POLLIN)

    def messageReceived(self, msg):
        while self.poller.poll(0):
            key = sys.stdin.read(1)
            if key == 'w':
                self.command("throttle", value=1)
            elif key == 'a':
                self.command('turn', value=1)
            elif key == 'd':
                self.command('turn', value=-1)
            elif key == ' ':
                self.command("fire")
            elif ord(key) == 3:
                reactor.stop()

    def process_message(self, message):
        # print message
        pass


def main():
    factory = ClientFactory()
    factory.protocol = ManualClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    fd = sys.stdin.fileno()
    tty.setraw(fd)
    try:
        reactor.callWhenRunning(main)
        reactor.run()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
