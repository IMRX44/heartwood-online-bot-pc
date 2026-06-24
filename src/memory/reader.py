"""Typed memory reader using pymem (Windows ReadProcessMemory).

Used as a fast, reliable alternative to vision for facts the game stores in
memory (exact HP, coordinates, item counts). Resolves pointer chains defined
in offsets.py.
"""
from __future__ import annotations

from typing import Optional

from src.memory import offsets
from src.utils.logger import get_logger

log = get_logger("memory")

try:
    import pymem
    _HAS_PYMEM = True
except Exception:  # pragma: no cover
    _HAS_PYMEM = False


class MemoryReader:
    def __init__(self, process_name: str = offsets.MODULE) -> None:
        self.process_name = process_name
        self._pm = None
        self._base = 0

    def attach(self) -> bool:
        if not _HAS_PYMEM:
            log.warning("pymem unavailable - memory backend disabled")
            return False
        try:
            self._pm = pymem.Pymem(self.process_name)
            module = pymem.process.module_from_name(
                self._pm.process_handle, self.process_name
            )
            self._base = module.lpBaseOfDll
            log.info("Attached to %s (base=0x%X)", self.process_name, self._base)
            return True
        except Exception as exc:
            log.error("Failed to attach to %s: %s", self.process_name, exc)
            return False

    def _resolve(self, ptr: offsets.Pointer) -> Optional[int]:
        """Walk a pointer chain to its final address."""
        if self._pm is None:
            return None
        addr = self._base + ptr.base_offset
        try:
            for off in ptr.chain[:-1]:
                addr = self._pm.read_longlong(addr) + off
            return addr + (ptr.chain[-1] if ptr.chain else 0)
        except Exception as exc:
            log.debug("Pointer resolve failed: %s", exc)
            return None

    def read_int(self, ptr: offsets.Pointer) -> Optional[int]:
        addr = self._resolve(ptr)
        if addr is None:
            return None
        try:
            return self._pm.read_int(addr)
        except Exception:
            return None

    def read_float(self, ptr: offsets.Pointer) -> Optional[float]:
        addr = self._resolve(ptr)
        if addr is None:
            return None
        try:
            return self._pm.read_float(addr)
        except Exception:
            return None

    # --- convenience accessors -----------------------------------------
    def hp(self) -> Optional[int]:
        return self.read_int(offsets.PLAYER_HP)

    def hp_percent(self) -> Optional[float]:
        cur, mx = self.read_int(offsets.PLAYER_HP), self.read_int(offsets.PLAYER_MAX_HP)
        if cur is None or not mx:
            return None
        return cur / mx

    def position(self) -> Optional[tuple[float, float]]:
        x, y = self.read_float(offsets.PLAYER_X), self.read_float(offsets.PLAYER_Y)
        return (x, y) if x is not None and y is not None else None

    def inventory_count(self) -> Optional[int]:
        return self.read_int(offsets.INVENTORY_COUNT)
