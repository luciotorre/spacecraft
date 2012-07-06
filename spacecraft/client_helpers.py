"""Helpers to make the universe less painful"""

from math import pi, atan2

TWO_PI = 2 * pi
PI = pi
MAX_TURN = pi / 8  # This will break when you can turn more than pi/8

def target_angle(currentx, currenty, targetx, targety):
    """Angle to look at target, in radians in [-PI, PI]"""
    return atan2(targety - currenty, targetx - currentx)


def relative_angle(currentx, currenty, targetx, targety, currentangle):
    """Angle to look at target relative to current angle.

    In multiples of 'turn' messages.
    """
    target = target_angle(currentx, currenty, targetx, targety)
    result = -(((target - currentangle) % TWO_PI) - PI) / MAX_TURN
    return result


