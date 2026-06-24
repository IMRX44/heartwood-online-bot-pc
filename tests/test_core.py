"""Tests for the framework's game-independent logic (no game required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.commands.interpreter import parse
from src.core.state_machine import StateMachine
from src.input.humanize import human_mouse_path
from src.navigation.pathfinding import astar


def test_command_parse_count():
    cmd = parse("fish until 100")
    assert cmd.task == "fish"
    assert cmd.kwargs["count"] == 100


def test_command_parse_duration():
    cmd = parse("gather ore for 30m")
    assert cmd.task == "gather"
    assert cmd.kwargs["duration"] == 1800
    assert cmd.kwargs["templates"] == ["ore_node.png"]


def test_command_parse_craft():
    cmd = parse("craft iron_bar x50")
    assert cmd.task == "craft"
    assert cmd.kwargs["count"] == 50
    assert cmd.kwargs["recipe"] == "iron_bar"


def test_command_parse_unknown():
    assert parse("dance forever") is None


def test_state_machine_runs_to_completion():
    sm = StateMachine("t")
    visited = []

    def a():
        visited.append("a")
        return "b"

    def b():
        visited.append("b")
        return None

    sm.add_state("a", a, initial=True)
    sm.add_state("b", b)
    sm.run()
    assert visited == ["a", "b"]


def test_mouse_path_starts_and_ends_correctly():
    path = human_mouse_path((0, 0), (100, 100))
    assert path[0] == (0, 0)
    assert path[-1] == (100, 100)
    assert len(path) > 2  # curved, not a straight jump


def test_astar_finds_path():
    grid = [[0, 0, 0],
            [1, 1, 0],
            [0, 0, 0]]
    path = astar(grid, (0, 0), (0, 2))
    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (0, 2)


def test_astar_blocked_returns_none():
    grid = [[0, 1, 0],
            [1, 1, 0],
            [0, 1, 0]]
    assert astar(grid, (0, 0), (2, 0)) is None
