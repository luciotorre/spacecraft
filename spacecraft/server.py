# -*- coding: utf-8 *-*
import json
import random

from Box2D import b2
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Factory
from twisted.application import service, internet
from twisted.python import usage, log
from twisted.internet import task, reactor

from spacecraft import euclid


class Map(service.Service):

    def __init__(self, xsize, ysize, frames=20):
        self.xsize = xsize
        self.ysize = ysize
        self.timeStep = 1. / frames
        self.vel_iters = 10
        self.pos_iters = 10
        self.step = 0

        self.world = b2.world(gravity=(0, 0), doSleep=True)
        self.clients = []

        self.update_loop = task.LoopingCall(self.doStep)

    def startService(self):
        self.update_loop.start(self.timeStep)

    def stopService(self):
        self.update_loop.stop()

    def doStep(self):
        for client in self.clients:
            client.execute()
        self.world.Step(self.timeStep, self.vel_iters, self.pos_iters)
        self.world.ClearForces()
        for client in self.clients:
            client.sendUpdate()
        self.step += 1

    def get_map_description(self):
        return dict(xsize=self.xsize, ysize=self.ysize)

    def register_client(self, client):
        self.clients.append(client)

    def unregister_client(self, client):
        self.clients.remove(client)


class ClientBase(LineReceiver):

    def lineReceived(self, line):
        try:
            d = self.decode(line)
        except ValueError:
            log.msg("invalid line:", line)
        else:
            self.messageReceived(d)

    def sendMessage(self, message):
        self.sendLine(self.encode(message))

    def decode(self, data):
        return json.loads(data)

    def encode(self, message):
        return json.dumps(message)

    def messageReceived(self, message):
        raise NotImplementedError()


class Client(ClientBase):
    def connectionLost(self, reason):
        log.msg("client connection lost:", (self.addr,))
        self.unregister()

    def unregister(self):
        self.map.unregister_client(self)

    def register(self, map):
        self.map = map
        map.register_client(self)

    def execute(self):
        pass

    def sendUpdate(self):
        self.sendMessage(dict(type="time", step=self.map.step))


class ClientFactory(Factory):
    def __init__(self, map):
        self.map = map

    def buildProtocol(self, addr):
        log.msg("Client connected from:", (addr,))
        protocol = Factory.buildProtocol(self, addr)
        protocol.register(self.map)
        protocol.addr = addr
        return protocol


class Player(Client):
    # the maximum possible force from the engines in newtons
    max_force = 100

    def __init__(self):
        self.throttle = 0

    def register(self, map):
        Client.register(self, map)
        self.create_player()

    def unregister(self):
        Client.unregister(self)
        self.map.world.DestroyBody(self.body)
        self.body = None

    def create_player(self):
        x = random.random() * self.map.xsize
        y = random.random() * self.map.ysize
        self.body = self.map.world.CreateDynamicBody(position=(x, y),
                                                userData=self)
        self.body.CreateCircleFixture(
            radius=1, density=1)

    def execute(self):
        if self.throttle != 0:
            force = euclid.Matrix3.new_rotate(self.body.angle) * \
                    euclid.Vector2(1, 0) * self.max_force * self.throttle
            self.body.ApplyForce(tuple(force), self.body.position)
            self.throttle = 0

    def get_repr(self):
        return dict(
            type="player",
            x=self.body.position[0], y=self.body.position[1],
            throttle=self.throttle)

    def messageReceived(self, message):
        msg_type = message.get("type", None)
        if msg_type is None:
            return
        meth = getattr(self, "do_" + msg_type, None)

        if meth is None:
            log.msg("Unknown message type:", msg_type)
            return

        meth(message)

    def do_throttle(self, message):
        value = message.get("value", 0)
        if not isinstance(value, (int, float)):
            log.msg("Bad throttle message:", message)

        self.throttle = max(0, min(1, value))


class PlayerFactory(ClientFactory):
    protocol = Player


class Monitor(Client):

    def register(self, map):
        Client.register(self, map)
        reactor.callLater(0, self.sendHello)

    def sendHello(self):
        m = self.map.get_map_description()
        m['type'] = "map_description"
        self.sendMessage(m)

    def sendUpdate(self):
        for body in self.map.world.bodies:
            self.sendMessage(body.userData.get_repr())
        self.sendMessage(dict(type="time", step=self.map.step))


class MonitorFactory(ClientFactory):
    protocol = Monitor


class Options(usage.Options):
    optParameters = [
        ["monitorport", "m", 11105,
            "The port number to listen on for monitors.", int],
        ["playerport", "p", 11106,
            "The port number to listen on for players.", int],
        ["xsize", "x", 1024,
            "The map x size.", int],
        ["ysize", "y", 1024,
            "The map y size.", int],

        ]


def makeService(options):
    root_service = service.MultiService()

    map = Map(options["xsize"], options["ysize"])
    map.setServiceParent(root_service)

    monitor_service = internet.TCPServer(
        options['monitorport'], MonitorFactory(map))
    monitor_service.setName("monitors")
    monitor_service.setServiceParent(root_service)

    player_service = internet.TCPServer(
        options['playerport'], PlayerFactory(map))
    player_service.setName("players")
    player_service.setServiceParent(root_service)

    return root_service
