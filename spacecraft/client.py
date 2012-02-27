# -*- coding: utf-8 *-*
"""
Creating a Spacecraft client
============================

Execution model
---------------

Game Status
^^^^^^^^^^^

World Update
^^^^^^^^^^^^


Incoming messages
-----------------

GPS Sensor
^^^^^^^^^^

{u'throttle': 0, u'sensor': u'gps', u'health': 100, u'position': [23.254238128662109, 18.901742935180664], u'velocity': [0.0, 0.0], u'angle': 0.0, u'type': u'player'}

Proximity Sensor
^^^^^^^^^^^^^^^^

{u'angle': 0.0, u'type': u'powerup', u'object_type': u'powerup', u'velocity': [0.0, 0.0], u'position': [15.404826164245605, 14.010764122009277], u'sensor': u'proximity', u'id': 49626320}
{u'throttle': 0, u'sensor': u'proximity', u'object_type': u'player', u'health': 90, u'position': [39.789058685302734, 4.5922360420227051], u'velocity': [2.7247390747070312, 0.0], u'angle': -26.31132698059082, u'type': u'player', u'id': 49624912}
{u'angle': 0.0, u'type': u'bullet', u'object_type': u'bullet', u'velocity': [-19.594663619995117, 34.871894836425781], u'position': [15.409300804138184, 42.053264617919922], u'sensor': u'proximity', u'id': 52035536}

Status Sensor
^^^^^^^^^^^^^

{u'sensor': u'status', u'health': 100}

Step
^^^^
{u'step': 637, u'type': u'time'}


Actions
-------

Using the monitor
-----------------

Objects Available
-----------------

Players
^^^^^^^

Bullets
^^^^^^^

Powerups
^^^^^^^^

Walls
^^^^^


"""
from twisted.internet import reactor

import spacecraft


class Client(spacecraft.server.ClientBase):
    def connectionLost(self, reason):
        reactor.stop()
