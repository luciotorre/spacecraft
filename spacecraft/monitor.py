# -*- coding: utf-8 *-*
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

import math
import pygame
import euclid

import spacecraft
from spacecraft.sparks import SparkEngine


class Scene:

    def __init__(self, screen):
        self.matrix = euclid.Matrix3.new_identity()
        self.screen = screen
        self.size = self.screen.get_size()

    def rotate(self, radians):
        self.matrix.rotate(radians)

    def translate(self, x, y):
        self.matrix.translate(x, y)

    def scale(self, size):
        self.matrix.scale(size, size)

    def to_screen(self, x, y):
        p = self.matrix * euclid.Point2(x, y)
        p.y = self.size[1] - p.y
        return int(p.x), int(p.y)


class Monitor(spacecraft.server.ClientBase):

    def __init__(self):
        self.messages = []
        self.font = pygame.font.Font(None, 18)
        self.avatars = {}
        # For now, just load our only avatar
        self.avatars['Ship'] = pygame.image.load('./static/img/Ship.bmp')

    @property
    def sparks(self):
        if not hasattr(self, '_sparks'):
            self._sparks = SparkEngine(self.screen)
        return self._sparks

    def messageReceived(self, message):
        kind = message.get("type", None)
        if kind == "time":
            self.update(self.messages + [message])
            self.messages = []
        elif kind == "map_description":
            # need to be smarter here, this works with current hardcoding
            self.scene.scale(7)
        else:
            self.messages.append(message)

    def update(self, messages):
        self.process_events()
        self.render_screen(messages)

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.transport.loseConnection()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.command("start_game")

    def render_screen(self, messages):
        self.screen.fill((0, 0, 0))
        for msg in messages:
            kind = msg.get("type", None)
            if kind == "player":
                position = self.scene.to_screen(*msg["position"])
                angle = msg['angle']
                # XXX achuni 2012-02-18: Why does 0.35 work? (Does it?)
                velocity = msg['velocity'][0] * 0.35, -msg['velocity'][1] * 0.35

                img = self.avatars['Ship']
                index = round(8 * angle / math.pi) % 16
                self.screen.blit(img, (position[0] - 12, position[1] - 12),
                    area=pygame.Rect(index * 24, 0, 24, 24))
                if msg.get('throttle', 0):
                    delta = euclid.Matrix3.new_rotate(-angle) * \
                        euclid.Vector2(-6, 0)
                    self.sparks.add_burst(position + delta, angle, velocity, 3)
                health = msg.get('health', 0)
                if health:
                    self.draw_health_bar(position, health)
            elif kind == "bullet":
                color = (255, 255, 255)
                position = self.scene.to_screen(*msg["position"])
                pygame.draw.circle(self.screen, color, position, 2)
            elif kind == "powerup":
                color = (255, 0, 0)
                position = self.scene.to_screen(*msg["position"])
                pygame.draw.circle(self.screen, color, position, 2)
            elif kind == "time":
                text = self.font.render("Step: %s" % (msg["step"],),
                    True, (255, 255, 255))
                where = text.get_rect()
                where.bottom = self.screen.get_height()
                where.left = 0
                self.screen.blit(text, where)
        self.sparks.step()
        pygame.display.flip()

    def connectionLost(self, reason):
        reactor.stop()

    def draw_health_bar(self, position, health, size=20):
        x, y = position[0] - size / 2, position[1] + size / 2 + 4
        if health > 50:
            color = (0, 255, 0)
        elif health > 20:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)
        rect = pygame.Rect(x, y, int(size * health / 100.), 4)
        pygame.draw.rect(self.screen, color, rect, 0)
        rect = pygame.Rect(x, y, size, 4)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)


class MonitorFactory(ClientFactory):
    protocol = Monitor

    def __init__(self, screen):
        self.screen = screen

    def buildProtocol(self, addr):
        proto = ClientFactory.buildProtocol(self, addr)
        proto.screen = self.screen
        proto.scene = Scene(self.screen)
        return proto

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()


def main():
    pygame.init()
    pygame.font.init()
    size = [700, 700]
    screen = pygame.display.set_mode(size)

    reactor.connectTCP("localhost", 11105, MonitorFactory(screen))


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
