# -*- coding: utf-8 *-*
from spacecraft.euclid import Matrix3
from twisted.trial.unittest import TestCase

from spacecraft import monitor


class MockScreen(object):
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height

    def get_size(self):
        return (self.width, self.height)


class TestScene(TestCase):
    def test_to_screen(self):
        scene = monitor.Scene(MockScreen())
        for (x, y) in [(0, 0), (500, 500), (0, 500), (123, 456)]:
            self.assertEqual((x, 600 - y), scene.to_screen(x, y))

