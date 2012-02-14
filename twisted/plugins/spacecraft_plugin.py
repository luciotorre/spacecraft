# -*- coding: utf-8 *-*
from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

import spacecraft


class SpaceCraftServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "spacecraft"
    description = "Runs the spacecraft server."
    options = spacecraft.server.Options

    def makeService(self, options):
        spacecraft_service = spacecraft.server.makeService(options)
        return spacecraft_service


serviceMaker = SpaceCraftServiceMaker()
