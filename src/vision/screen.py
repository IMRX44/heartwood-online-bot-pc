"""Fast screen capture, scoped to the game window when possible."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from src.utils.logger import get_logger

log = get_logger("vision.screen")

try:
    import mss
    _HAS_MSS = True
except Exception:  # pragma: no cover
    _HAS_MSS = False

Region = Tuple[int, int, int, int]  # left, top, width, height


class ScreenCapture:
    """Grabs frames as BGR numpy arrays (OpenCV-friendly)."""

    def __init__(self, region: Optional[Region] = None) -> None:
        self.region = region
        self._sct = mss.mss() if _HAS_MSS else None
        if self._sct is None:
            log.warning("mss unavailable - screen capture disabled")

    def set_region(self, region: Region) -> None:
        self.region = region

    def grab(self, region: Optional[Region] = None) -> Optional[np.ndarray]:
        """Return a BGR frame, or None if capture is unavailable."""
        if self._sct is None:
            return None
        region = region or self.region
        if region is None:
            monitor = self._sct.monitors[1]  # primary screen
        else:
            l, t, w, h = region
            monitor = {"left": l, "top": t, "width": w, "height": h}
        raw = self._sct.grab(monitor)
        frame = np.asarray(raw)  # BGRA
        return frame[:, :, :3]  # drop alpha -> BGR
