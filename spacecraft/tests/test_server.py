# -*- coding: utf-8 *-*
from mock import Mock
from twisted.trial.unittest import TestCase
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import defer, reactor

from spacecraft import server, world


def update_collector(target):
    def update_collect(*args, **kwargs):
        if args and kwargs:
            raise TypeError("cant use both args and kwargs.")

        if args and len(args) == 1:
            target.append(args[0])

        if kwargs:
            target.append(kwargs)

    return update_collect


class TestService(TestCase):

    def setUp(self):
        self.service = server.makeService(server.Options())
        self.service.startService()

    def tearDown(self):
        self.service.stopService()

    @defer.inlineCallbacks
    def connect_to(self, port):
        class ClientFactory(Factory):
            def buildProtocol(self, addr):
                return Protocol()

        point = TCP4ClientEndpoint(reactor, "localhost", port)
        protocol = yield point.connect(ClientFactory())
        defer.returnValue(protocol)

    @defer.inlineCallbacks
    def test_monitor(self):
        protocol = yield self.connect_to(11105)
        mf = self.service.getServiceNamed("monitors").args[1]
        self.assertEquals(len(mf.map.clients), 1)
        protocol.transport.loseConnection()

    @defer.inlineCallbacks
    def test_player(self):
        protocol = yield self.connect_to(11106)
        mf = self.service.getServiceNamed("monitors").args[1]
        self.assertEquals(len(mf.map.clients), 1)
        protocol.transport.loseConnection()


class TestGame(TestCase):

    def setUp(self):
        self.map = world.Game(100, 100)

    def create_player(self):
        player = server.Player()
        player.transport = Mock()
        player.register(self.map)
        reactor.iterate()
        return player

    def test_create_player(self):
        player = self.create_player()
        self.assertEquals(len(self.map.world.bodies), 1)
        prepr = player.object.get_full_position()
        self.assertTrue("position" in prepr)

    def test_monitor(self):
        player = self.create_player()
        monitor = server.Monitor()
        monitor.register(self.map)
        result = []
        monitor.sendMessage = update_collector(result)
        monitor.sendUpdate()
        self.assertEquals(len(result), 2)
        for p in ["angle", "velocity", "position"]:
            self.assertEquals(result[0][p],
                player.object.get_full_position()[p])

    def test_throttle(self):
        player = self.create_player()
        player.messageReceived(dict(type="throttle", value=0.5))
        self.assertEquals(player.object.throttle, 0.5)

    def test_turn(self):
        player = self.create_player()
        player.messageReceived(dict(type="turn", value=-0.5))
        self.assertEquals(player.object.turn, -0.5)

    def test_fire(self):
        player = self.create_player()
        player.messageReceived(dict(type="fire"))
        self.assertEquals(player.object.fire, 1)

    def test_gps(self):
        player = self.create_player()
        result = []
        player.sendMessage = update_collector(result)
        player.sendUpdate()
        result = [r for r in result if "sensor" in r and r["sensor"] == "gps"]

        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]["position"],
            tuple(player.object.body.position))

    def test_radar(self):
        player = self.create_player()
        player.object.sensors.append(world.RadarSensor(player.object))
        player.object.body.position = (100, 100)

        player2 = self.create_player()
        player2.object.body.position = (120, 100)

        result = []
        player.sendMessage = update_collector(result)
        player.sendUpdate()
        result = [r for r in result if "sensor" in r and r["sensor"] == "radar"]

        self.assertNotEquals(len(result), 1)
        self.assertEquals(result[0]["position"],
            tuple(player2.object.body.position))
