# -*- coding: utf-8 *-*
from xml.etree.ElementTree import ElementTree

import Box2D

from spacecraft import world


class Wall(world.ObjectBase):

    def __init__(self, game, node):
        self.node = node
        super(Wall, self).__init__(game)
        self.map.register_wall(self)

    def create_body(self, _x, _y):
        self.x = float(self.node.attrib["x"])
        self.y = float(self.node.attrib["y"])
        self.width = float(self.node.attrib["width"])
        self.height = float(self.node.attrib["height"])
        self.body = self.map.world.CreateStaticBody(
            position=(self.x + self.width / 2, self.y + self.height / 2),
            shapes=Box2D.b2PolygonShape(box=(self.width / 2, self.height / 2)),
            userData=self,
            )

    def get_type(self):
        return "wall"

    def get_description(self):
        return {'type': 'wall', 'x': self.x, 'y': self.y, 'width': self.width,
            'height': self.height}

class MapLoader(object):

    def __init__(self, filename):
        self.etree = ElementTree().parse(filename)

        self.open_methods = {
            "{http://www.w3.org/2000/svg}rect": self.open_rect,
            "engine-force-powerup": self.open_engine_force_powerup,
            "proximity-mine": self.proximity_mine,
            }

        self.close_methods = {
            }

    def setup_map(self, game):
        self.process_node(self.etree, game)

    def process_node(self, node, game):
        if "game-tag" in node.attrib:
            tag = node.attrib["game-tag"]
        else:
            tag = node.tag

        if tag in self.open_methods:
            self.open_methods[tag](node, game)

        for subnode in node:
            self.process_node(subnode, game)

        if tag in self.close_methods:
            self.close_methods[tag](node, game)

    def open_rect(self, node, game):
        Wall(game, node)

    def open_engine_force_powerup(self, node, game):
        sodipodi = "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}"
        x = float(node.attrib[sodipodi + "cx"])
        y = float(node.attrib[sodipodi + "cy"])
        print "powerup", x, y
        world.EngineForcePowerUp(game, x, y)

    def proximity_mine(self, node, game):
        sodipodi = "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}"
        world.ProximityMine(game,
            float(node.attrib[sodipodi + "cx"]),
            float(node.attrib[sodipodi + "cy"]))
