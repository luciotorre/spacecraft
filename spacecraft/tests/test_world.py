# -*- coding: utf-8 *-*
from unittest import TestCase

from spacecraft import world


class TestCollision(TestCase):

    def test_powerup_collide(self):
        map = world.Game(1024, 768)
        o1 = world.PowerUp(map, 100, 100)
        result1 = []
        o1.contact = result1.append
        o2 = world.PowerUp(map, 100, 100)
        self.assertTrue(o2.body in map.world.bodies)
        map.step_world()
        self.assertEquals(result1, [o2])
        self.assertFalse(o2.body in map.world.bodies)


class TestWorld(TestCase):

    def test_wraparound(self):
        map = world.Game(1024, 768)
        o1 = world.PowerUp(map, 1024 + 100, 100)
        map.step_world()
        self.assertEquals(o1.body.position[0], 100)


class TestPowerUp(TestCase):

    def test_increase_force(self):
        map = world.Game(1024, 768)
        pu = world.EngineForcePowerUp(map, 100, 100)
        pl = world.PlayerObject(map, 100, 100)
        old_force = pl.max_force
        map.step_world()
        self.assertEquals(pl.max_force, old_force * pu.increase)
        self.assertFalse(pu.body in map.world.bodies)
