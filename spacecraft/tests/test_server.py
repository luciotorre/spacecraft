# -*- coding: utf-8 *-*
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


class TestMap(TestCase):

    def test_create_player(self):
        map = world.Map(100, 100)
        player = server.Player()
        player.register(map)
        self.assertEquals(len(map.world.bodies), 1)
        prepr = player.object.get_repr()
        self.assertTrue("x" in prepr)
        self.assertTrue("y" in prepr)

    def test_monitor(self):
        map = world.Map(100, 100)
        player = server.Player()
        player.register(map)
        monitor = server.Monitor()
        monitor.register(map)
        result = []
        monitor.sendMessage = update_collector(result)
        monitor.sendUpdate()
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0], player.object.get_repr())

    def test_throttle(self):
        map = world.Map(100, 100)
        player = server.Player()
        player.register(map)
        player.messageReceived(dict(type="throttle", value=0.5))
        self.assertEquals(player.throttle, 0.5)

    def test_gps(self):
        map = world.Map(100, 100)
        player = server.Player()
        player.register(map)
        result = []
        player.sendMessage = update_collector(result)
        player.sendUpdate()
        result = [r for r in result if r["type"] == "gps"]

        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]["position"],
            tuple(player.object.body.position))

    def test_radar(self):
        map = world.Map(100, 100)
        player = server.Player()
        player.register(map)
        player.object.body.position = (100, 100)

        player2 = server.Player()
        player2.register(map)
        player2.object.body.position = (200, 100)

        result = []
        player.sendMessage = update_collector(result)
        player.sendUpdate()
        result = [r for r in result if r["type"] == "radar"]

        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]["position"],
            tuple(player2.object.body.position))
