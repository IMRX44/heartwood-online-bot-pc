"""Game protocol parser.

PLACEHOLDER schema. Reverse the real wire format with Wireshark while playing
(see docs/CALIBRATION.md), then implement parse_payload(). Most game protocols
are length-prefixed: [u16 length][u8 opcode][payload...]. Adjust to taste.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

log = get_logger("network.parser")


@dataclass
class GameEvent:
    opcode: int
    name: str
    data: Dict[str, Any]


# TODO: map real opcodes once reversed.
OPCODES = {
    0x01: "player_move",
    0x02: "hp_update",
    0x03: "loot_drop",
    0x04: "chat_message",
}


def parse_payload(payload: bytes) -> Optional[GameEvent]:
    """Decode a single packet payload into a GameEvent, if recognized."""
    if len(payload) < 3:
        return None
    try:
        length, opcode = struct.unpack_from("<HB", payload, 0)
    except struct.error:
        return None
    name = OPCODES.get(opcode)
    if name is None:
        return None
    body = payload[3:3 + max(0, length)]
    # TODO: decode `body` per-opcode into structured fields.
    return GameEvent(opcode=opcode, name=name, data={"raw": body})
