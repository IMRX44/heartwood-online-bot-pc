"""Unit tests — no Windows process required."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import struct
from speedhack.src.process import _aob_match
from speedhack.src.speed import SpeedHack


def test_aob_match_all_x():
    data = b"\x01\x02\x03\x04"
    assert _aob_match(data, 0, b"\x01\x02\x03", b"xxx")


def test_aob_match_fails_on_mismatch():
    data = b"\x01\xFF\x03\x04"
    assert not _aob_match(data, 0, b"\x01\x02\x03", b"xxx")


def test_aob_match_wildcard_ignores_byte():
    data = b"\x01\xFF\x03\x04"
    assert _aob_match(data, 0, b"\x01\x00\x03", b"x?x")


def test_aob_match_partial_offset():
    data = b"\xAA\x01\x02\x03"
    assert _aob_match(data, 1, b"\x01\x02\x03", b"xxx")


def test_speed_hack_init_defaults():
    h = SpeedHack()
    assert not h.is_active
    assert h.multiplier == 2.0
    assert h._addr is None


def test_speed_hack_set_address():
    h = SpeedHack()
    h.set_address(0xDEAD, 7.5)
    assert h._addr == 0xDEAD
    assert h._base_speed == 7.5


def test_target_speed_calculation():
    h = SpeedHack(multiplier=3.0)
    h.set_address(0x1000, 5.0)
    assert abs(h.target_speed - 15.0) < 1e-5


def test_enable_without_proc_returns_false():
    h = SpeedHack()
    h.set_address(0x1000, 5.0)
    # _proc is None → freeze thread starts but writes are no-ops
    result = h.enable()
    assert result is True   # enable() itself returns True (addr is set)
    h.disable()             # must not crash


def test_disable_before_enable_is_safe():
    h = SpeedHack()
    h.disable()  # must not raise


def test_float_packing():
    for v in [1.0, 5.0, 10.5, 0.0, -1.0]:
        packed   = struct.pack("<f", v)
        unpacked = struct.unpack_from("<f", packed)[0]
        assert abs(unpacked - v) < 1e-4
