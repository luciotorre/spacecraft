# -*- coding: utf-8 *-*
import random

from spacecraft import map

from shapely.geometry import Polygon
from spacecraft import euclid

class MapLoader(map.MapLoader):

    def __init__(self, filename):
        super(MapLoader, self).__init__(filename)

        self.open_methods = {
            "{http://www.w3.org/2000/svg}rect": self.open_rect,
            }

        self.close_methods = {
            }


    def open_rect(self, node, game, transform):
        x = float(node.attrib["x"])
        y = float(node.attrib["y"])
        x += transform["translate"][0]
        y += transform["translate"][1]
        width = float(node.attrib["width"])
        height = float(node.attrib["height"])
        game.add_wall(x, y, width, height)

class GridMap(object):

    xsize = 300
    ysize = 300
    xbuckets = ybuckets = 50


    def __init__(self, filename):
        l = MapLoader(filename)
        self.walls = []
        l.setup_map(self)
        self.build_grid()
        self.goal = None
        self.goal_grid = [ [float("+inf")] * self.ybuckets for i in range(self.xbuckets) ]

    def build_grid(self):
        self.grid = [ [0] * self.ybuckets for i in range(self.xbuckets) ]
        for xb in range(self.xbuckets):
            for yb in range(self.ybuckets):
                cell = self.build_cell(xb, yb)
                if not self.intersects(cell):
                    self.grid[xb][yb] = 1

    def add_wall(self, x, y, w, h):
        self.walls.append(
            Polygon([
                (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
                ])
            )

    def build_cell(self, xb, yb):
        box_w = self.xsize / self.xbuckets

        x = xb * box_w
        y = yb * box_w
        w = h = box_w

        return Polygon([
                (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
                ])

    def cell_to_world(self, xb, yb):
        box_w = self.xsize / self.xbuckets

        x = xb * box_w
        y = yb * box_w

        return x, y

    def world_to_cell(self, x, y):
        box_w = self.xsize / self.xbuckets

        nx = int(x / box_w)
        ny = int(y / box_w)
        return nx, ny

    def intersects(self, obj):
        return any(
            w.intersects(obj) for w in self.walls
            )

    def dump(self):
        for yp in range(self.ybuckets):
            print "".join(str(self.grid[xp][yp])
                    for xp in range(self.xbuckets))

    def dump_search_state(self, open, closed, start, goal):
        for yp in range(self.ybuckets):
            parts = []
            for xp in range(self.xbuckets):
                if (xp, yp) == goal:
                    val = 'G'
                elif (xp, yp) == start:
                    val = 'S'
                elif (xp, yp) in open:
                    val = '*'
                elif (xp, yp) in closed:
                    val = '^'
                else:
                    val = str(self.grid[xp][yp])

                parts.append( val )
            print "".join(parts)

    def dump_path(self, start, goal, path, X=[]):
        for yp in range(self.ybuckets):
            parts = []
            for xp in range(self.xbuckets):
                if (xp, yp) in X:
                    val = ' '
                elif (xp, yp) == goal:
                    val = 'G'
                elif (xp, yp) == start:
                    val = 'S'
                elif (xp, yp) in path:
                    val = '*'
                else:
                    val = str(self.grid[xp][yp])

                parts.append(val)
            print "".join(parts)

    def heuristic_cost_estimate(self, start, goal):
        return self.dist_between(start, goal)

    def dist_between(self, current, neighbor):
        o = euclid.Point2(*current)
        e = euclid.Point2(*neighbor)
        return abs(o - e)

    def neighbor_nodes(self, node):
        x, y = node
        result = []
        for xd in [-1, 0, 1]:
            for yd in [-1, 0, 1]:
                nx = x + xd
                ny = y + yd

                if nx >= self.xbuckets:
                    continue

                if ny >= self.ybuckets:
                    continue

                if nx < 0:
                    continue
                if ny < 0:
                    continue

                if (nx, ny) == node:
                    continue

                if self.grid[nx][ny] == 0:
                    continue

                result.append((nx, ny))
        return result

    def find_path(self, start, goal, debug=False):
        closedset = set()
        openset = set([start])
        came_from = {}

        g_score = {}
        f_score = {}

        # Cost from start along best known path.
        g_score[start] = 0

        # Estimated total cost from start to goal through y.
        f_score[start] = g_score[start] + self.heuristic_cost_estimate(start, goal)

        while openset:
            if debug:
                self.dump_search_state(openset, closedset, start, goal)
                raw_input("[enter]")
            current = winner(openset, f_score)
            if current == goal:
                return reconstruct_from_path(came_from, goal)

            openset.remove(current)
            closedset.add(current)

            for neighbor in self.neighbor_nodes(current):
                if neighbor in closedset:
                    continue

                tentative_g_score = g_score[current] + \
                    self.dist_between(current, neighbor)

                if neighbor not in openset or \
                         tentative_g_score < g_score[neighbor]:
                    openset.add(neighbor)
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + \
                        self.heuristic_cost_estimate(neighbor, goal)

        raise ValueError()

    def _visible(self, start, end):
        """line algo."""
        steps = line(start, end)
        for s in steps:
            if self.grid[s[0]][s[1]] == 0:
                return False
        return True

    def is_wall(self, pos):
        x, y = self.world_to_cell(*pos)
        if self.grid[x][y] == 1:
            return True
        return False

    def visible(self, start, end):
        _start = self.world_to_cell(*start)
        _end = self.world_to_cell(*end)
        return self._visible(_start, _end)

    def waypoint(self, start, goal):
        """In world coordinates!"""
        _start = self.world_to_cell(*start)
        _goal = self.world_to_cell(*goal)
        try:
            p = self.find_path(_start, _goal)
        except ValueError:
            print "*DEBUG" * 100
            p = self.find_path(_start, _goal, debug=True)
        if random.random() < 0.01:
            self.dump_path(_start, _goal, p)
        if len(p) < 2:
            return goal
        way = p[1]
        for w in p[1:]:
            if self._visible(_start, w):
                way = w
            else:
                break
        return self.cell_to_world(*way)

    def set_goal(self, goal):
        self.goal = self.world_to_cell(*goal)

        Q = set()
        self.goalpath = D = {}
        for x in range(self.xbuckets):
            for y in range(self.ybuckets):
                Q.add((x, y))
                D[(x,y)] = float("+inf")
        D[self.goal] = 0

        while Q:
            current = winner(Q, D)
            if current is None:
                break

            Q.remove(current)

            for n in self.neighbor_nodes(current):
                alt = D[current] + self.dist_between(current, n)
                if alt < D[n]:
                    D[n] = alt

    def towards_goal_from(self, current):
        p = self.world_to_cell(*current)

        #n = winner(self.neighbor_nodes(p), self.goalpath)
        #return self.cell_to_world(*n)
        # old
        goal = p
        step = 0
        while True:
            np = winner(self.neighbor_nodes(goal), self.goalpath)
            if not self._visible(p, np):
                break
            goal = np
            step += 1
            if step > 10:
                break
        return self.cell_to_world(*goal)

    def dump_goal(self):
        m = max(f for f in self.goalpath.values() if f < 1000)
        for yp in range(self.ybuckets):
            parts = []
            for xp in range(self.xbuckets):
                if (xp, yp) == self.goal:
                    val = 'G'
                elif self.goalpath[(xp, yp)] > 1000:
                    val = '*'
                else:
                    val = str(int(self.goalpath[(xp,yp)]*10./m))

                parts.append(val)
            print "".join(parts)

def line(start, end):
    result = []
    x0, y0 = start
    x1, y1 = end

    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1

    if x0 > x1:
        x0, x1 = x1, x0
        y0, y1 = y1, y0

    if y0 < y1:
        ystep = 1
    else:
        ystep = -1

    deltax = x1 - x0
    deltay = abs(y1 - y0)
    error = 0
    y = y0

    for x in range(x0, x1 + 1):  # We add 1 to x1 so that the range includes x1
        if steep:
            result.append((y, x))
        else:
            result.append((x, y))

        error = error + deltay
        if (error << 1) >= deltax:
            y = y + ystep
            error = error - deltax

    return result


def winner(nodes, scores):
    winner = None
    dist = float("+inf")
    for n in nodes:
        d = scores[n]
        if d < dist:
            winner = n
            dist = d
    return winner


def reconstruct_from_path(came_from, current_node):
    if current_node in came_from:
        p = reconstruct_from_path(came_from, came_from[current_node])
        return p + [current_node]
    else:
        return [current_node]


if __name__ == "__main__":
    g = GridMap("maps/cross.svg")
    g.dump()
    s = (3,3)
    e = (47, 47)
    import time
    t = time.time()
    p = g.find_path(s, e)
    print time.time() - t
    g.dump_path(s, e, p)
    print p
    s = 10, 10
    e = 290, 290
    print "waypoint", g.waypoint(s, e)
    g.set_goal((96, 290))
    g.dump_goal()
    print g.towards_goal_from((10, 10))
