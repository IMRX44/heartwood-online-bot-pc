"""Global hotkey listener for toggle and panic.

Registers callbacks for:
  - toggle key (default F1) — enable/disable speed hack
  - panic key  (default F12) — immediate disable + exit

Uses pynput so it works while the game window has focus.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

try:
    from pynput import keyboard
    _HAS_PYNPUT = True
except Exception:
    _HAS_PYNPUT = False


class HotkeyManager:
    def __init__(
        self,
        toggle_key: str = "f1",
        panic_key:  str = "f12",
    ) -> None:
        self.toggle_key = toggle_key
        self.panic_key  = panic_key
        self._on_toggle: Optional[Callable[[], None]] = None
        self._on_panic:  Optional[Callable[[], None]] = None
        self._listener: Optional[object]              = None

    def register(
        self,
        on_toggle: Callable[[], None],
        on_panic:  Callable[[], None],
    ) -> bool:
        if not _HAS_PYNPUT:
            return False
        self._on_toggle = on_toggle
        self._on_panic  = on_panic

        def _press(key):
            name = getattr(key, "name", None) or str(key).strip("'")
            if name == self.toggle_key and self._on_toggle:
                self._on_toggle()
            elif name == self.panic_key and self._on_panic:
                self._on_panic()

        self._listener = keyboard.Listener(on_press=_press)
        self._listener.daemon = True  # type: ignore[union-attr]
        self._listener.start()        # type: ignore[union-attr]
        return True

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()  # type: ignore[union-attr]
