# -*- coding: utf-8 *-*
import random
import math

from Box2D import b2
import Box2D

from twisted.application import service
from twisted.internet import task

from spacecraft import euclid

STATUS_WAITING = "waiting"
STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"


class Game(service.Service):

    def __init__(self, xsize, ysize, frames=20):
        self.xsize = xsize
        self.ysize = ysize
        self.timeStep = 1. / frames
        self.vel_iters = 10
        self.pos_iters = 10
        self.step = 0

        self.world = b2.world(gravity=(0, 0), doSleep=True)
        self.clients = []
        self.objects = []
        self.status = STATUS_WAITING
        self.winner = None
        self.update_loop = task.LoopingCall(self.doStep)

    def start_game(self):
        self.status = STATUS_RUNNING
        self.notifyEvent(type="game_status", current=self.status)

    def finish_game(self, winner):
        self.status = STATUS_FINISHED
        self.winner = winner
        self.notifyEvent(type="game_status", current=self.status)

    def startService(self):
        self.update_loop.start(self.timeStep)

    def stopService(self):
        self.update_loop.stop()

    def notifyEvent(self, **kwargs):
        for client in self.clients:
            client.sendMessage(**kwargs)

    def doStep(self):
        if self.status is STATUS_RUNNING:
            for object in self.objects:
                object.execute()
            self.step_world()
            self.step += 1

        for client in self.clients:
            client.sendUpdate()

    def step_world(self):
        self.world.Step(self.timeStep, self.vel_iters, self.pos_iters)
        self.world.ClearForces()
        for contact in self.world.contacts:
            if not contact.touching:
                continue
            o1 = contact.fixtureA.body.userData
            o2 = contact.fixtureB.body.userData
            o1.contact(o2)
            o2.contact(o1)
        # wraparound
        for body in self.world.bodies:
            x, y = body.position
            body.position = (x % self.xsize), (y % self.ysize)

    def get_map_description(self):
        return dict(xsize=self.xsize, ysize=self.ysize)

    def register_client(self, client):
        self.clients.append(client)

    def unregister_client(self, client):
        self.clients.remove(client)

    def register_object(self, obj):
        self.objects.append(obj)

    def unregister_object(self, obj):
        self.objects.remove(obj)


class ObjectBase(object):

    def __init__(self, map, x=None, y=None):
        self.map = map
        self.create_body(x, y)

    def create_body(self):
        raise NotImplementedError()

    def get_repr(self):
        return dict(
            type=self.get_type(),
            x=self.body.position[0], y=self.body.position[1])

    def get_type(self):
        return "object"

    def get_id(self):
        return id(self)

    def get_full_position(self):
        return dict(position=tuple(self.body.position),
            angle=self.body.angle,
            velocity=tuple(self.body.linearVelocity))

    def destroy(self):
        if self.body is not None:
            self.map.world.DestroyBody(self.body)
            self.body = None

    def contact(self, other):
        """This object is in contact with other."""


class PowerUp(ObjectBase):

    def get_type(self):
        return "powerup"

    def create_body(self, x=None, y=None):
        if x is None:
            x = random.random() * self.map.xsize
        if y is None:
            y = random.random() * self.map.ysize
        self.body = self.map.world.CreateDynamicBody(position=(x, y),
                                                userData=self)
        self.body.CreateCircleFixture(radius=1, density=1)

    def contact(self, other):
        self.destroy()


class EngineForcePowerUp(PowerUp):
    increase = 1.2

    def contact(self, other):
        if isinstance(other, PlayerObject):
            other.max_force *= self.increase
        super(EngineForcePowerUp, self).contact(other)


class GpsSensor(object):

    def __init__(self, player):
        self.player = player

    def getReadings(self):
        return [dict(type="gps",
            position=(self.player.body.position[0],
                    self.player.body.position[1]))]


class RayCastCallback(Box2D.b2RayCastCallback):
    """
    This class captures the closest hit shape.
    """
    def __init__(self):
        super(RayCastCallback, self).__init__()
        self.fixture = None

    # Called for each fixture found in the query. You control how the ray
    # proceeds by returning a float that indicates the fractional length of
    # the ray. By returning 0, you set the ray length to zero. By returning
    # the current fraction, you proceed to find the closest point.
    # By returning 1, you continue with the original ray clipping.
    def ReportFixture(self, fixture, point, normal, fraction):
        self.fixture = fixture
        self.point = Box2D.b2Vec2(point)
        self.normal = Box2D.b2Vec2(normal)
        return fraction


class RadarSensor(object):
    steps = 360
    distance = 500

    def __init__(self, player):
        self.player = player

    def getReadings(self):
        ray = euclid.Vector2(self.distance, 0)
        rotate = euclid.Matrix3.new_rotate(2 * math.pi / self.steps)

        for step in range(self.steps):
            callback = RayCastCallback()

            point1 = self.player.body.position
            point2 = tuple(ray + self.player.body.position)
            ray = rotate * ray
            self.player.map.world.RayCast(callback, point1, point2)
            if callback.fixture is not None:
                yield dict(type="radar",
                    object_type=callback.fixture.body.userData.get_type(),
                    id=callback.fixture.body.userData.get_id(),
                    **callback.fixture.body.userData.get_full_position())


class PlayerObject(ObjectBase):
    # the maximum possible force from the engines in newtons
    max_force = 10
    # the maximum instant turn per step, in radians
    max_turn = 0.1
    # number of steps that it takes for weapon to reload
    reload_delay = 10

    def __init__(self, map, x=None, y=None):
        super(PlayerObject, self).__init__(map, x, y)
        self.sensors = [GpsSensor(self), RadarSensor(self)]
        self.throttle = 0
        self.turn = 0
        self.fire = 0
        self.reloading = 0
        self.map.register_object(self)

    def execute(self):
        body = self.body
        if self.turn:
            body.angle = (body.angle + self.max_turn *
                self.turn) % (2 * math.pi)
            self.turn = 0
        if self.throttle != 0:
            force = euclid.Matrix3.new_rotate(body.angle) * \
                    euclid.Vector2(1, 0) * self.max_force * \
                    self.throttle
            body.ApplyForce(tuple(force), body.position)
            self.throttle = 0
        if self.reloading:
            self.reloading -= 1
        else:
            if self.fire:
                x, y = body.position
                speedx, speedy = euclid.Matrix3.new_rotate(body.angle) * \
                    euclid.Vector2(15, 0) + body.linearVelocity
                Bullet(self.map, x, y, speedx, speedy)
                self.reloading = self.reload_delay
                self.fire = 0

    def get_type(self):
        return "player"

    def create_body(self, x=None, y=None):
        if x is None:
            x = random.random() * self.map.xsize
        if y is None:
            y = random.random() * self.map.ysize
        self.body = self.map.world.CreateDynamicBody(position=(x, y),
                                                userData=self)
        self.body.CreateCircleFixture(radius=1, density=1)


class Bullet(ObjectBase):
    total_ttl = 100

    def __init__(self, map, x, y, speedx=None, speedy=None):
        self.map = map
        self.ttl = self.total_ttl
        self.create_body(x, y, speedx, speedy)
        self.map.register_object(self)

    def execute(self):
        self.ttl -= 1
        if self.ttl <= 0:
            self.map.unregister_object(self)
            self.map.world.DestroyBody(self.body)

    def get_type(self):
        return "bullet"

    def create_body(self, x, y, speedx=None, speedy=None):
        if speedx is None:
            speedx = random.random() * self.map.xsize
        if speedy is None:
            speedy = random.random() * self.map.ysize
        self.body = self.map.world.CreateKinematicBody(position=(x, y),
            linearVelocity=(speedx, speedy), userData=self)
