# -*- coding: utf-8 *-*
from unittest import TestCase
from mock import Mock

from spacecraft import map, world


class TestWall(TestCase):
    def setUp(self):
        self.game = Mock()
        self.node = Mock()
        self.node.attrib = {'x': 123, 'y': 234, 'width': 345, 'height': 456}
        
    def test_init_registers_wall(self):
        wall = map.Wall(self.game, self.node)
        self.game.assertEqual(1, self.game.register_wall.call_count)
        self.assertEqual(123, wall.x)

    def test_inits_from_node(self):
        wall = map.Wall(self.game, self.node)
        self.assertEqual(123, wall.x)
        self.assertEqual(234, wall.y)
        self.assertEqual(345, wall.width)
        self.assertEqual(456, wall.height)

    def test_get_description(self):
        wall = map.Wall(self.game, self.node)
        expected = {'type': 'wall', 'x': 123, 'y': 234, 'width': 345,
            'height': 456}
        self.assertEqual(expected, wall.get_description())

    def test_get_type(self):
        wall = map.Wall(self.game, self.node)
        self.assertEqual('wall', wall.get_type())

    def test_body_created_correctly(self):
        game = world.Game(1024, 1024)
        wall = map.Wall(game, self.node)
        self.assertEqual(1, len(game.world.bodies))
        body = game.world.bodies[0]
        self.assertEqual(wall, body.userData)
        self.assertEqual(123 + 345 / 2., body.position[0])
        self.assertEqual(234 + 456 / 2., body.position[1])
        expected = [(-172.5, -228), (172.5, -228), (172.5, 228), (-172.5, 228)]
        self.assertEqual(expected, body.fixtures[0].shape.vertices)