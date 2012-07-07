"""Helpers to make the universe less painful"""

from math import pi, atan2

from spacecraft import euclid

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
    t = euclid.Point2(targetx, targety)
    c = euclid.Point2(currentx, currenty)
    v_new = euclid.Matrix3.new_rotate(-currentangle) * (t - c)

    result = target_angle(0, 0, v_new.x, v_new.y) / MAX_TURN
    return result


