"""A* pathfinding over a 2D walkability grid.

The grid (0 = walkable, 1 = blocked) can be built from the minimap, a baked
collision map, or memory-read tile data. Returns a list of waypoints.
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

Cell = Tuple[int, int]


def _heuristic(a: Cell, b: Cell) -> float:
    # Octile distance (allows diagonal movement).
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (1.41421356 - 2) * min(dx, dy)


def astar(grid: List[List[int]], start: Cell, goal: Cell) -> Optional[List[Cell]]:
    """Return a path from start to goal, or None if unreachable."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    if not (0 <= start[1] < rows and 0 <= start[0] < cols):
        return None

    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1),
                 (-1, -1), (-1, 1), (1, -1), (1, 1)]

    open_heap: List[Tuple[float, Cell]] = [(0.0, start)]
    came_from: Dict[Cell, Cell] = {}
    g_score: Dict[Cell, float] = {start: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current)

        cx, cy = current
        for dx, dy in neighbors:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < cols and 0 <= ny < rows):
                continue
            if grid[ny][nx] != 0:
                continue
            step = 1.41421356 if dx and dy else 1.0
            tentative = g_score[current] + step
            neighbor = (nx, ny)
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + _heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    return None


def _reconstruct(came_from: Dict[Cell, Cell], current: Cell) -> List[Cell]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
