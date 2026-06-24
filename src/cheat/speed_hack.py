"""Speed Hack — multiplies the player's movement-speed value in memory.

How it works
------------
1. Attach to the game process via WriteProcessMemory.
2. Find the speed float in memory:
   - **Pointer mode** (preferred): follow the chain in `offsets.py` once
     it's been reverse-engineered with Cheat Engine.
   - **AOB scan mode** (fallback): scan all readable pages for the unique
     byte sequence that surrounds the speed value and lock onto it.
3. A background "freeze" thread re-writes the hacked value ~60×/s so the
   game can't reset it on the server tick.
4. Toggle on/off via `SpeedHack.enable()` / `.disable()`.

Anti-detection notes
--------------------
- Use a multiplier ≤ 2.0 — extreme values are easy to flag server-side.
- Randomize the multiplier slightly each write (±2%) to avoid a flat signal.
- The freeze thread jitters its interval (15–20 ms) to avoid a fixed pattern.

Calibration
-----------
Set SPEED_AOB_PATTERN / SPEED_AOB_MASK to the bytes Cheat Engine shows
around the speed float, then set SPEED_AOB_OFFSET to the number of bytes
from the match start to the float itself.
"""
from __future__ import annotations

import random
import struct
import threading
import time
from typing import Optional

from src.cheat.memory_utils import MemoryHandle, open_process_by_name
from src.utils.logger import get_logger

log = get_logger("cheat.speed")

# ---------------------------------------------------------------------------
# Calibration placeholders — fill in after Cheat Engine work.
# ---------------------------------------------------------------------------

# AOB signature: bytes around the speed float (add ?-wildcards for unknowns).
# Example: b"\x00\x00\x80\x3f\x00\x00\xc8\x42"  (1.0f then 100.0f nearby)
SPEED_AOB_PATTERN: bytes = b"\x00\x00\x80\x3f"   # placeholder: 1.0f LE
SPEED_AOB_MASK:    bytes = b"xxxx"                # all bytes must match
SPEED_AOB_OFFSET:  int   = 0                      # bytes from match start to float

# Default movement speed (used to validate found addresses).
EXPECTED_BASE_SPEED: float = 5.0    # TODO: measure in-game


class SpeedHack:
    """Modifies the player movement speed in a running Heartwood process."""

    def __init__(
        self,
        process_name: str = "Heartwood.exe",
        multiplier: float = 2.0,
    ) -> None:
        self.process_name = process_name
        self.multiplier = multiplier

        self._handle: Optional[MemoryHandle] = None
        self._speed_addr: Optional[int] = None
        self._base_speed: float = 0.0

        self._active = False
        self._freeze_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # --- attachment -----------------------------------------------------
    def attach(self) -> bool:
        """Open a handle to the game and find the speed address."""
        h = open_process_by_name(self.process_name)
        if h is None:
            log.error("Could not find process '%s'", self.process_name)
            return False
        self._handle = h
        log.info("Attached to %s", self.process_name)
        return self._find_speed_address()

    def detach(self) -> None:
        self.disable()
        if self._handle:
            self._handle.close()
            self._handle = None

    # --- address discovery ---------------------------------------------
    def _find_speed_address(self) -> bool:
        """
        Try to locate the speed float via AOB scan.
        Returns True if a plausible address was found.
        """
        if self._handle is None:
            return False

        log.info("AOB scanning for speed float (pattern=%s)…", SPEED_AOB_PATTERN.hex())
        candidates = []
        for addr in self._handle.aob_scan(SPEED_AOB_PATTERN, SPEED_AOB_MASK):
            float_addr = addr + SPEED_AOB_OFFSET
            val = self._handle.read_float(float_addr)
            if val is not None and 0.5 <= val <= 50.0:
                candidates.append((float_addr, val))
                log.debug("  candidate 0x%X  value=%.4f", float_addr, val)
            if len(candidates) >= 20:
                break

        if not candidates:
            log.warning("No speed address found — calibrate AOB in speed_hack.py")
            return False

        # Prefer the candidate whose value is closest to EXPECTED_BASE_SPEED.
        best_addr, best_val = min(candidates,
                                  key=lambda x: abs(x[1] - EXPECTED_BASE_SPEED))
        self._speed_addr = best_addr
        self._base_speed = best_val
        log.info("Speed address: 0x%X  base=%.4f", best_addr, best_val)
        return True

    def set_address(self, address: int, base_speed: float) -> None:
        """Manually set the speed address (skip AOB scan) when offsets are known."""
        self._speed_addr = address
        self._base_speed = base_speed
        log.info("Speed address set manually: 0x%X  base=%.4f", address, base_speed)

    # --- enable / disable ----------------------------------------------
    def enable(self) -> bool:
        if self._speed_addr is None:
            log.error("Speed address unknown — call attach() first")
            return False
        if self._active:
            return True
        self._active = True
        self._stop_event.clear()
        self._freeze_thread = threading.Thread(
            target=self._freeze_loop, daemon=True, name="speed-freeze"
        )
        self._freeze_thread.start()
        log.info("Speed hack ENABLED  multiplier=%.2f×", self.multiplier)
        return True

    def disable(self) -> None:
        if not self._active:
            return
        self._active = False
        self._stop_event.set()
        if self._freeze_thread:
            self._freeze_thread.join(timeout=1.0)
        # Restore original speed.
        if self._handle and self._speed_addr:
            self._handle.write_float(self._speed_addr, self._base_speed)
        log.info("Speed hack DISABLED  speed restored to %.4f", self._base_speed)

    @property
    def is_active(self) -> bool:
        return self._active

    # --- freeze loop ---------------------------------------------------
    def _freeze_loop(self) -> None:
        """Re-write the hacked speed ~60 Hz with slight jitter (anti-flatline)."""
        while not self._stop_event.is_set():
            if self._handle and self._speed_addr:
                # ±2% jitter on the multiplier to avoid a perfectly flat signal.
                jitter = random.uniform(0.98, 1.02)
                hacked = self._base_speed * self.multiplier * jitter
                self._handle.write_float(self._speed_addr, hacked)
            self._stop_event.wait(timeout=random.uniform(0.015, 0.020))

    # --- live read (for UI display) ------------------------------------
    def current_speed(self) -> Optional[float]:
        if self._handle and self._speed_addr:
            return self._handle.read_float(self._speed_addr)
        return None
