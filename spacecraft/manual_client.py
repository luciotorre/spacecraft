# -*- coding: utf-8 *-*
import pygame

from twisted.internet import reactor

from spacecraft.monitor import Monitor, MonitorFactory


class ManualClient(Monitor):
    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.transport.loseConnection()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.command("fire")
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.command("turn", value=1)
        elif keys[pygame.K_RIGHT]:
            self.command("turn", value=-1)

        if keys[pygame.K_UP]:
            self.command("throttle", value=1)

    def process_message(self, message):
        # print message
        pass


class ManualClientFactory(MonitorFactory):
    protocol = ManualClient


def main():
    pygame.init()
    pygame.font.init()
    size = [700, 700]
    screen = pygame.display.set_mode(size)

    reactor.connectTCP("localhost", 11106, ManualClientFactory(screen))


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
