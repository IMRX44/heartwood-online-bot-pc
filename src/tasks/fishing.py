"""Auto-fishing task.

State flow:
  cast -> wait_for_bite -> reel -> (loot) -> cast ...

Bite detection uses vision (splash/bobber template) by default, and can be
upgraded to packet- or memory-driven detection when those backends are wired.
"""
from __future__ import annotations

import time

from src.input.humanize import jittered
from src.tasks.base import Task
from src.utils.logger import get_logger

log = get_logger("task.fishing")


class FishingTask(Task):
    name = "fish"

    def build(self) -> None:
        tcfg = self.ctx.config.tasks.get("fishing", {})
        self.cast_key = tcfg.get("cast_key", "1")
        self.bobber = tcfg.get("bobber_template", "bobber.png")
        self.splash = tcfg.get("splash_template", "splash.png")

        self.fsm.add_state("cast", self._cast, initial=True)
        self.fsm.add_state("wait_for_bite", self._wait_for_bite)
        self.fsm.add_state("reel", self._reel)

    def _cast(self) -> str | None:
        if self.should_stop():
            return None
        log.debug("Casting line")
        self.ctx.input.press_key(self.cast_key)
        time.sleep(jittered(1.0, 2.0))  # wait for bobber to settle
        self._bite_deadline = time.time() + 30  # max wait for a bite
        return "wait_for_bite"

    def _wait_for_bite(self) -> str | None:
        """Watch the bobber region for the splash that signals a bite."""
        frame = self.ctx.frame()
        if frame is not None:
            splash = self.ctx.detector.find_template(frame, self.splash)
            if splash is not None:
                log.debug("Bite detected (conf=%.2f)", splash.confidence)
                return "reel"
        if time.time() > self._bite_deadline:
            log.debug("No bite - recasting")
            return "cast"
        time.sleep(0.1)
        return "wait_for_bite"

    def _reel(self) -> str | None:
        log.debug("Reeling in")
        self.ctx.input.press_key(self.cast_key)  # same key reels in most games
        time.sleep(jittered(0.8, 1.5))
        self.on_success()
        return "cast"
