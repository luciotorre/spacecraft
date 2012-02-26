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

    def test_events(self):
        map = world.Game(100, 100)

        class Mock:
            pass

        result = []
        mock = Mock()
        mock.sendMessage = lambda **kwargs: result.append(kwargs)
        map.clients.append(mock)
        map.start_game()
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0],
            dict(type="game_status", current=world.STATUS_RUNNING))

        map.finish_game(None)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[1],
            dict(type="game_status", current=world.STATUS_FINISHED))

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


class TestProximitySensor(TestCase):

    def test_report(self):
        map = world.Game(100, 100)
        pu = world.EngineForcePowerUp(map, 60, 60)
        pl = world.PlayerObject(map, 50, 50)
        sensor = world.ProximitySensor(pl)
        result = list(sensor.getReadings())
        self.assertEquals(pu.body.position, result[0]["position"])
