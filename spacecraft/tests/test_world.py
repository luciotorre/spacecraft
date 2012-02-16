# -*- coding: utf-8 *-*
from unittest import TestCase

from spacecraft import world


class TestCollision(TestCase):

    def test_powerup_collide(self):
        map = world.Map(1024, 768)
        o1 = world.PowerUp(map, 100, 100)
        o2 = world.PowerUp(map, 100, 100)
        self.assertEquals(len(map.world.contacts), 0)
        map.step_world()
        self.assertEquals(len(map.world.contacts), 1)
        map.step_world()
        self.assertEquals(len(map.world.contacts), 1)
