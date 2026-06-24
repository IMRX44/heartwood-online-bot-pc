"""Memory offsets for Heartwood Online.

These are PLACEHOLDERS. Find the real values with Cheat Engine against the
running client (see docs/CALIBRATION.md), then fill them in here. A pointer
chain is expressed as a base module offset plus a list of dereference offsets.

Example of how to find them:
  1. Cheat Engine -> attach to Heartwood.exe
  2. Scan for your current HP, take damage, rescan, repeat -> green address
  3. "Find out what writes to this address" -> walk back to a static pointer
  4. Record base + offset chain below.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Pointer:
    base_offset: int                       # offset from module base
    chain: List[int] = field(default_factory=list)  # successive dereferences


MODULE = "Heartwood.exe"

# TODO: replace 0x0 placeholders with real values from Cheat Engine.
PLAYER_HP = Pointer(base_offset=0x0, chain=[0x0])
PLAYER_MAX_HP = Pointer(base_offset=0x0, chain=[0x0])
PLAYER_MP = Pointer(base_offset=0x0, chain=[0x0])
PLAYER_X = Pointer(base_offset=0x0, chain=[0x0])
PLAYER_Y = Pointer(base_offset=0x0, chain=[0x0])
INVENTORY_COUNT = Pointer(base_offset=0x0, chain=[0x0])
