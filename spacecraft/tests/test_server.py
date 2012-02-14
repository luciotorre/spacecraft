# -*- coding: utf-8 *-*
from twisted.trial.unittest import TestCase
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import defer, reactor

from spacecraft import server


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
        map = server.Map(100, 100)
        player = server.Player()
        player.register(map)
        self.assertEquals(len(map.world.bodies), 1)
        prepr = player.get_repr()
        self.assertTrue("x" in prepr)
        self.assertTrue("y" in prepr)

    def test_monitor(self):
        map = server.Map(100, 100)
        player = server.Player()
        player.register(map)
        monitor = server.Monitor()
        monitor.register(map)
        result = []
        monitor.sendMessage = result.append
        monitor.sendUpdate()
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0], player.get_repr())

    def test_throttle(self):
        map = server.Map(100, 100)
        player = server.Player()
        player.register(map)
        player.messageReceived(dict(type="throttle", value=0.5))
        self.assertEquals(player.throttle, 0.5)
