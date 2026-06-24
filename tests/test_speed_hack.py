"""Tests for speed hack logic that don't require a Windows process."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct
from src.cheat.memory_utils import _match
from src.cheat.speed_hack import SpeedHack


def test_aob_match_exact():
    data = b"\x01\x02\x03\x04\x05"
    assert _match(data, 0, b"\x01\x02\x03", b"xxx")
    assert not _match(data, 0, b"\x01\xFF\x03", b"xxx")


def test_aob_match_wildcard():
    data = b"\x01\x99\x03\x04"
    # middle byte is wildcard — should match regardless of 0x99
    assert _match(data, 0, b"\x01\x00\x03", b"x?x")


def test_speed_hack_init():
    h = SpeedHack(process_name="Heartwood.exe", multiplier=2.0)
    assert not h.is_active
    assert h.multiplier == 2.0


def test_speed_hack_manual_address():
    h = SpeedHack()
    h.set_address(0xDEADBEEF, 5.0)
    assert h._speed_addr == 0xDEADBEEF
    assert h._base_speed == 5.0


def test_speed_hack_enable_without_handle_is_safe():
    h = SpeedHack()
    h.set_address(0x1000, 5.0)
    # No real process — enable() should return False cleanly, not crash.
    result = h.enable()
    # _handle is None so freeze thread will be started but writes are no-ops.
    # We just ensure it doesn't raise.
    h.disable()


def test_float_pack_roundtrip():
    """Ensure our struct packing is consistent with what we'd write/read."""
    val = 7.5
    packed = struct.pack("<f", val)
    unpacked = struct.unpack_from("<f", packed)[0]
    assert abs(unpacked - val) < 1e-5
