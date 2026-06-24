"""SpeedHack — locates the movement-speed float and patches it in real time.

Strategy
--------
1.  Attach via ProcessHandle.
2a. If a pointer chain is supplied (found with Cheat Engine), follow it.
2b. Otherwise run an AOB scan to discover the address dynamically.
3.  Spawn a *freeze thread* that re-writes the value at ~60 Hz with ±2 %
    random jitter so anti-cheat systems don't see a flat write pattern.
4.  On disable(), restore the original value.

Calibrating for Heartwood Online
---------------------------------
See docs/HOW_TO_FIND_SPEED.md.
"""
from __future__ import annotations

import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from speedhack.src.process import ProcessHandle, open_by_name

# --------------------------------------------------------------------------
# Calibration — fill in after Cheat Engine work (see docs/HOW_TO_FIND_SPEED.md)
# --------------------------------------------------------------------------

# An AOB signature around the speed float.
# Use '?' as wildcard bytes.  Example:
#   PATTERN = bytes([0x00, 0x00, 0x80, 0x3F, 0x00, 0x00])
#   MASK    = b"xxxx??"
# Placeholder (4 bytes that encode 1.0f little-endian):
AOB_PATTERN: bytes = bytes([0x00, 0x00, 0x80, 0x3F])
AOB_MASK:    bytes = b"xxxx"
AOB_OFFSET:  int   = 0    # bytes from match start → float

# Expected base speed (used to filter implausible AOB hits).
BASE_SPEED_HINT: float = 5.0


@dataclass
class PointerChain:
    """Static base-module offset + dereference chain, from Cheat Engine."""
    module_offset: int
    offsets: List[int] = field(default_factory=list)


class SpeedHack:
    def __init__(
        self,
        process_name: str    = "Heartwood.exe",
        multiplier:   float  = 2.0,
        pointer:      Optional[PointerChain] = None,
    ) -> None:
        self.process_name = process_name
        self.multiplier   = multiplier
        self.pointer      = pointer          # set once Cheat Engine work is done

        self._proc:        Optional[ProcessHandle] = None
        self._addr:        Optional[int]           = None
        self._base_speed:  float                   = 0.0

        self._active      = False
        self._stop        = threading.Event()
        self._thread:     Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Attachment
    # ------------------------------------------------------------------
    def attach(self) -> bool:
        proc = open_by_name(self.process_name)
        if proc is None:
            return False
        self._proc = proc

        if self.pointer:
            return self._resolve_pointer()
        return self._aob_scan()

    def detach(self) -> None:
        self.disable()
        if self._proc:
            self._proc.close()
            self._proc = None

    def set_address(self, addr: int, base_speed: float) -> None:
        """Skip all scanning and hard-pin an address (from Cheat Engine)."""
        self._addr       = addr
        self._base_speed = base_speed

    # ------------------------------------------------------------------
    # Address discovery
    # ------------------------------------------------------------------
    def _resolve_pointer(self) -> bool:
        assert self._proc and self.pointer
        # TODO: resolve module base via EnumProcessModules, then walk chain.
        # Placeholder — returns False until implemented.
        return False

    def _aob_scan(self) -> bool:
        assert self._proc
        candidates = []
        for hit in self._proc.aob_scan(AOB_PATTERN, AOB_MASK):
            addr = hit + AOB_OFFSET
            val  = self._proc.read_float(addr)
            if val is not None and 0.1 <= val <= 100.0:
                candidates.append((addr, val))
            if len(candidates) >= 30:
                break

        if not candidates:
            return False

        # Keep the hit whose value is closest to the expected base speed.
        best_addr, best_val = min(candidates,
                                  key=lambda x: abs(x[1] - BASE_SPEED_HINT))
        self._addr       = best_addr
        self._base_speed = best_val
        return True

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------
    def enable(self) -> bool:
        if self._addr is None:
            return False
        if self._active:
            return True
        self._active = True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._freeze, daemon=True, name="speed-freeze"
        )
        self._thread.start()
        return True

    def disable(self) -> None:
        if not self._active:
            return
        self._active = False
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        # Restore original speed.
        if self._proc and self._addr:
            self._proc.write_float(self._addr, self._base_speed)

    @property
    def is_active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Live read (for UI)
    # ------------------------------------------------------------------
    def current_speed(self) -> Optional[float]:
        if self._proc and self._addr:
            return self._proc.read_float(self._addr)
        return None

    @property
    def target_speed(self) -> float:
        return self._base_speed * self.multiplier

    # ------------------------------------------------------------------
    # Freeze thread
    # ------------------------------------------------------------------
    def _freeze(self) -> None:
        while not self._stop.is_set():
            if self._proc and self._addr:
                jitter   = random.uniform(0.98, 1.02)     # ±2 % noise
                hacked   = self._base_speed * self.multiplier * jitter
                self._proc.write_float(self._addr, hacked)
            self._stop.wait(timeout=random.uniform(0.015, 0.020))  # ~60 Hz
