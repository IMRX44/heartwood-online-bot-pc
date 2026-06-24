"""Keyboard / mouse controller with a human-like feel.

Wraps pynput (mouse) and pydirectinput (keys) so the rest of the codebase has
a clean, testable interface. Falls back to no-op stubs when the libraries or a
display are unavailable (e.g. CI), so imports never crash.
"""
from __future__ import annotations

import time
from typing import Tuple

from src.core.config import InputConfig
from src.input.humanize import human_mouse_path, jittered
from src.utils.logger import get_logger

log = get_logger("input")

Point = Tuple[int, int]

try:
    from pynput.mouse import Button, Controller as MouseController
    _HAS_MOUSE = True
except Exception:  # pragma: no cover - headless environments
    _HAS_MOUSE = False

try:
    import pydirectinput
    pydirectinput.PAUSE = 0  # we manage our own delays
    _HAS_KEYS = True
except Exception:  # pragma: no cover
    _HAS_KEYS = False


class InputController:
    def __init__(self, cfg: InputConfig) -> None:
        self.cfg = cfg
        self._mouse = MouseController() if _HAS_MOUSE else None
        if not (_HAS_MOUSE and _HAS_KEYS):
            log.warning("Input libraries unavailable - running in dry-run mode")

    # --- timing ---------------------------------------------------------
    def _action_pause(self) -> None:
        lo, hi = self.cfg.action_delay
        time.sleep(jittered(lo, hi))

    # --- mouse ----------------------------------------------------------
    def move_to(self, target: Point) -> None:
        if self._mouse is None:
            log.debug("[dry-run] move_to %s", target)
            return
        start = self._mouse.position
        path = human_mouse_path((int(start[0]), int(start[1])), target)
        lo, hi = self.cfg.mouse_move_duration
        per_step = jittered(lo, hi) / max(1, len(path))
        for pt in path:
            self._mouse.position = pt
            time.sleep(per_step)

    def click(self, target: Point | None = None, button: str = "left") -> None:
        if target is not None:
            self.move_to(target)
        if self._mouse is None:
            log.debug("[dry-run] click %s %s", button, target)
            return
        btn = Button.right if button == "right" else Button.left
        self._mouse.press(btn)
        time.sleep(jittered(0.04, 0.12))  # human press duration
        self._mouse.release(btn)
        self._action_pause()

    # --- keyboard -------------------------------------------------------
    def press_key(self, key: str) -> None:
        if not _HAS_KEYS:
            log.debug("[dry-run] press_key %s", key)
            return
        pydirectinput.keyDown(key)
        time.sleep(jittered(0.03, 0.09))
        pydirectinput.keyUp(key)
        self._action_pause()

    def hold_key(self, key: str, duration: float) -> None:
        if not _HAS_KEYS:
            log.debug("[dry-run] hold_key %s for %.2fs", key, duration)
            return
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)
        self._action_pause()
