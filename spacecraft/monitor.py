# -*- coding: utf-8 *-*
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor

import math
import pygame
import euclid

import spacecraft
from spacecraft import world
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


class Message(object):

    def __init__(self, size=36):
        self.message = None
        self.font = pygame.font.Font(None, size)

    def set(self, message):
        self.message = message

    def clear(self):
        self.message = None

    def render(self, screen, where=None):
        if not self.message:
            return

        text = self.font.render(self.message,
            True, (255, 255, 255))
        if where is None:
            where = text.get_rect()
            where.centerx = screen.get_width() / 2
            where.centery = screen.get_height() / 2
        screen.blit(text, where)


class Monitor(spacecraft.server.ClientBase):

    def __init__(self):
        self.messages = []
        self.font = pygame.font.Font(None, 18)
        self.avatars = {}
        # For now, just load our only avatar
        self.avatars['Ship'] = pygame.image.load('./static/img/Ship.bmp')
        self.message = Message()
        self.terrain = []

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
            self.terrain = message.get('terrain', [])
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

    def process_message(self, message):
        pass

    def draw_avatar(self, position, angle, velocity, throttle=None,
        health=None, avatar='Ship', name=None):
        position = self.scene.to_screen(*position)
        # XXX achuni 2012-02-18: Why does 0.35 work? (Does it?)
        velocity = velocity[0] * 0.35, -velocity[1] * 0.35
        img = self.avatars[avatar]
        index = round(8 * angle / math.pi) % 16
        self.screen.blit(img, (position[0] - 12, position[1] - 12),
                         area=pygame.Rect(index * 24, 0, 24, 24))
        if throttle:
            delta = euclid.Matrix3.new_rotate(-angle) * \
                euclid.Vector2(-6, 0)
            self.sparks.add_burst(
                position + delta, angle, velocity, 3)
        if health:
            self.draw_health_bar(position, health)
        if name:
            self.draw_name(position, name)

    def draw_name(self, position, name):
        font_size = 16
        approx_size = int(len(name) * font_size * 0.35)
        x, y = position[0] - approx_size / 2, position[1] - (font_size + 10)
        pos = self.scene.to_screen(*position)
        msg = Message(font_size)
        msg.set(name)
        msg.render(self.screen, (x, y))

    def draw_player(self, data):
        return self.draw_avatar(data['position'], data['angle'], data['velocity'],
                                name=str(data['name']))

    def draw_bullet(self, msg):
        color = (255, 255, 255)
        pos = self.scene.to_screen(*msg["position"])
        pygame.draw.circle(self.screen, color, pos, 2)

    def draw_powerup(self, msg):
        color = (255, 0, 0)
        pos = self.scene.to_screen(*msg["position"])
        pygame.draw.circle(self.screen, color, pos, 2)

    def draw_mine(self, msg):
        color = (0, 0, 150)
        pos = self.scene.to_screen(*msg["position"])
        pygame.draw.circle(self.screen, color, pos, 3)

    def render_screen(self, messages):
        self.screen.fill((0, 0, 0))
        for wall in self.terrain:
            x, y = self.scene.to_screen(wall['x'], wall['y'])
            w = int(wall['width'] * 7) # Because 7 works
            h = int(wall['height'] * 7)
            y = y - h
            rect = pygame.Rect(x, y, w, h)
            pygame.draw.rect(self.screen, (100, 100, 100), rect, 0)
        for msg in messages:
            kind = msg.get("type", None)
            if kind == "monitor":
                # God-like view of the world.
                object_type = msg.get("object_type")
                if object_type == "player":
                    msg.pop('object_type')
                    msg.pop('type')
                    self.draw_avatar(**msg)
                elif hasattr(self, 'draw_' + object_type):
                    getattr(self, 'draw_' + object_type)(msg)
            elif kind == 'sensor':
                # Avatar's view of the world.
                if 'gps' in msg:
                    data = msg['gps']
                    if 'status' in msg:
                        data.update(msg['status'])
                    self.draw_avatar(**data)
                for reading in msg.get('proximity', []):
                    object_type = reading.get("object_type")
                    if hasattr(self, 'draw_' + object_type):
                        getattr(self, 'draw_' + object_type)(reading)

            elif kind == "time":
                text = self.font.render("Step: %s" % (msg["step"],),
                    True, (255, 255, 255))
                where = text.get_rect()
                where.bottom = self.screen.get_height()
                where.left = 0
                self.screen.blit(text, where)
            elif kind == "game_status":
                if msg["current"] == world.STATUS_RUNNING:
                    self.message.clear()
                elif msg["current"] == world.STATUS_WAITING:
                    self.message.set("Waiting...")
                elif msg["current"] == world.STATUS_FINISHED:
                    self.message.set("Finished.")
            self.process_message(msg)
        self.sparks.step()
        self.message.render(self.screen)
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
    pygame.display.set_caption('monitor')
    screen = pygame.display.set_mode(size)

    reactor.connectTCP("localhost", 11105, MonitorFactory(screen))


if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
    pygame.quit()
