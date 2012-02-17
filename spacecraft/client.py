# -*- coding: utf-8 *-*
from twisted.internet import reactor

import spacecraft


class Client(spacecraft.server.ClientBase):
    def connectionLost(self, reason):
        reactor.stop()
