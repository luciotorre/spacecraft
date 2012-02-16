# -*- coding: utf-8 *-*
import random

from Box2D import b2

from twisted.application import service
from twisted.internet import task


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


class ObjectBase(object):

    def __init__(self, map):
        self.map = map
        self.create_body()

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
        self.map.world.DestroyBody(self.body)
        self.body = None


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


class PlayerObject(ObjectBase):

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
