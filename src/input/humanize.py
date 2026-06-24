"""Human-like input helpers: Bézier mouse paths and randomized timing.

Robotic, pixel-perfect, fixed-interval input is the single biggest tell for
anti-cheat. These helpers add organic noise so movements and delays look human.
"""
from __future__ import annotations

import random
from typing import List, Tuple

Point = Tuple[int, int]


def _bezier(p0: Point, p1: Point, p2: Point, p3: Point, steps: int) -> List[Point]:
    """Cubic Bézier curve sampled into `steps` integer points."""
    pts: List[Point] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt**3 * p0[0] + 3 * mt**2 * t * p1[0]
             + 3 * mt * t**2 * p2[0] + t**3 * p3[0])
        y = (mt**3 * p0[1] + 3 * mt**2 * t * p1[1]
             + 3 * mt * t**2 * p2[1] + t**3 * p3[1])
        pts.append((int(round(x)), int(round(y))))
    return pts


def human_mouse_path(start: Point, end: Point, steps: int | None = None) -> List[Point]:
    """Generate a curved, slightly-overshooting path between two points."""
    dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    if steps is None:
        steps = max(12, int(dist / 12))

    # Two control points offset perpendicular-ish to create a natural arc.
    def jitter(a: Point, b: Point) -> Point:
        mx = a[0] + (b[0] - a[0]) * random.uniform(0.2, 0.8)
        my = a[1] + (b[1] - a[1]) * random.uniform(0.2, 0.8)
        spread = max(8, dist * 0.15)
        return (int(mx + random.uniform(-spread, spread)),
                int(my + random.uniform(-spread, spread)))

    c1, c2 = jitter(start, end), jitter(start, end)
    path = _bezier(start, c1, c2, end, steps)

    # Occasionally overshoot the target then correct, like a real hand.
    if dist > 200 and random.random() < 0.3:
        over = (end[0] + random.randint(-15, 15), end[1] + random.randint(-15, 15))
        path += _bezier(end, over, over, end, max(4, steps // 4))
    return path


def jittered(low: float, high: float) -> float:
    """A random delay in [low, high] seconds."""
    return random.uniform(low, high)


def gaussian_delay(mean: float, spread: float = 0.05) -> float:
    """A positive normally-distributed delay around `mean` seconds."""
    return max(0.0, random.gauss(mean, spread))
