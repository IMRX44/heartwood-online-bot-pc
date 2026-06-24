"""Auto-combat / grinding task.

State flow:
  find_target -> engage -> rotate -> (heal) -> loot -> find_target ...

Targets the nearest mob (vision or YOLO), runs an ability rotation, watches HP
(memory if available, else OCR/health-bar vision) and pots when low.
"""
from __future__ import annotations

import time
from typing import List, Optional

from src.input.humanize import jittered
from src.tasks.base import Task
from src.utils.logger import get_logger

log = get_logger("task.combat")


class CombatTask(Task):
    name = "combat"

    def build(self) -> None:
        tcfg = self.ctx.config.tasks.get("combat", {})
        self.rotation: List[str] = tcfg.get("rotation", ["1", "2", "3"])
        self.hp_pot_key = tcfg.get("hp_pot_key", "5")
        self.hp_threshold = tcfg.get("hp_threshold", 0.35)
        self.mob_template = self.kwargs.get("mob_template", "mob.png")
        self._rotation_idx = 0

        self.fsm.add_state("find_target", self._find_target, initial=True)
        self.fsm.add_state("engage", self._engage)
        self.fsm.add_state("rotate", self._rotate)
        self.fsm.add_state("loot", self._loot)

    # --- helpers --------------------------------------------------------
    def _hp_percent(self) -> Optional[float]:
        """Prefer memory; fall back to a vision-based health bar read."""
        if self.ctx.memory is not None:
            pct = self.ctx.memory.hp_percent()
            if pct is not None:
                return pct
        return None  # TODO: add health-bar pixel read as vision fallback

    def _check_heal(self) -> None:
        pct = self._hp_percent()
        if pct is not None and pct < self.hp_threshold:
            log.info("HP %.0f%% - using potion", pct * 100)
            self.ctx.input.press_key(self.hp_pot_key)

    def _nearest_mob(self):
        frame = self.ctx.frame()
        if frame is None:
            return None
        # Prefer YOLO detections, fall back to template matching.
        candidates = self.ctx.detector.detect_objects(frame)
        candidates += self.ctx.detector.find_all_templates(frame, self.mob_template)
        if not candidates:
            return None
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        return min(candidates,
                   key=lambda m: (m.center[0] - cx) ** 2 + (m.center[1] - cy) ** 2)

    # --- states ---------------------------------------------------------
    def _find_target(self) -> Optional[str]:
        if self.should_stop():
            return None
        mob = self._nearest_mob()
        if mob is None:
            self.ctx.input.press_key("d")  # patrol to find mobs
            time.sleep(jittered(0.5, 1.0))
            return "find_target"
        self._target = mob
        return "engage"

    def _engage(self) -> Optional[str]:
        log.debug("Engaging mob at %s", self._target.center)
        self.ctx.input.click(self._target.center)  # target it
        self.ctx.input.press_key("tab")            # fallback target lock
        self._fight_deadline = time.time() + 20
        return "rotate"

    def _rotate(self) -> Optional[str]:
        self._check_heal()
        key = self.rotation[self._rotation_idx % len(self.rotation)]
        self.ctx.input.press_key(key)
        self._rotation_idx += 1
        time.sleep(jittered(0.6, 1.1))  # global cooldown-ish

        # TODO: detect target death (mob HP bar gone / memory). For now use a
        # timeout heuristic before moving to loot.
        if time.time() > self._fight_deadline:
            return "loot"
        return "rotate"

    def _loot(self) -> Optional[str]:
        log.debug("Looting")
        self.ctx.input.press_key("f")  # common loot key
        time.sleep(jittered(0.5, 1.0))
        self.on_success()
        return "find_target"
