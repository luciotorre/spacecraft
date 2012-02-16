# -*- coding: utf-8 *-*
import random

from Box2D import b2

from twisted.application import service
from twisted.internet import task

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
            for client in self.clients:
                client.execute()
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


class PlayerObject(ObjectBase):
    # the maximum possible force from the engines in newtons
    max_force = 100

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
