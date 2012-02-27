# -*- coding: utf-8 *-*
"""
Creating a Spacecraft client
============================

Communications
--------------

The game server communicates with players and monitors using tcp. One port
for each kind of client. It comunicates by asynchronous message passing.

The protocol is line oriented, each line is a json encoded dict with the
message.

Execution model
---------------

Game Status
^^^^^^^^^^^

World Update
^^^^^^^^^^^^

Incoming messages for monitors
------------------------------

Monitors know everything that is going on in the game and get messages
with all the information of each body present in the game.

Incoming messages for players
-----------------------------

Players dont get global knowledge of the game, just the information provided
by whatever sensors are active in the game and some general game status
information.

All messages have the "type" attribute, which will let you know the type of
message it is.

Step
^^^^
type == 'time'
Contains a step attribute that shows the number of steps that have passed since
the game started running. The step number will not move when the game is in
waiting state.

Example:
    {u'step': 637, u'type': u'time'}


Status Sensor
^^^^^^^^^^^^^
type == 'sensor' and sensor == 'status'

Internal player information.

{u'sensor': u'status', u'health': 100}

GPS Sensor
^^^^^^^^^^
type == 'sensor' and sensor == 'gps'

Your current position.

{u'throttle': 0, u'sensor': u'gps', u'health': 100, u'position': [23.254238128662109, 18.901742935180664], u'velocity': [0.0, 0.0], u'angle': 0.0, u'type': u'player'}

Proximity Sensor
^^^^^^^^^^^^^^^^

{u'angle': 0.0, u'type': u'powerup', u'object_type': u'powerup', u'velocity': [0.0, 0.0], u'position': [15.404826164245605, 14.010764122009277], u'sensor': u'proximity', u'id': 49626320}
{u'throttle': 0, u'sensor': u'proximity', u'object_type': u'player', u'health': 90, u'position': [39.789058685302734, 4.5922360420227051], u'velocity': [2.7247390747070312, 0.0], u'angle': -26.31132698059082, u'type': u'player', u'id': 49624912}
{u'angle': 0.0, u'type': u'bullet', u'object_type': u'bullet', u'velocity': [-19.594663619995117, 34.871894836425781], u'position': [15.409300804138184, 42.053264617919922], u'sensor': u'proximity', u'id': 52035536}



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
