"""Auto-gathering task (mining / woodcutting / herbalism).

State flow:
  scan -> approach -> harvest -> scan ...

Finds the nearest resource node on screen, walks the mouse to it, interacts,
waits for the gather cast, then looks for the next node.
"""
from __future__ import annotations

import time
from typing import List, Optional

from src.input.humanize import jittered
from src.tasks.base import Task
from src.utils.logger import get_logger

log = get_logger("task.gathering")


class GatheringTask(Task):
    name = "gather"

    def build(self) -> None:
        tcfg = self.ctx.config.tasks.get("gathering", {})
        self.interact_key = tcfg.get("interact_key", "e")
        self.templates: List[str] = self.kwargs.get(
            "templates", tcfg.get("resource_templates", ["ore_node.png"])
        )
        self._target = None

        self.fsm.add_state("scan", self._scan, initial=True)
        self.fsm.add_state("approach", self._approach)
        self.fsm.add_state("harvest", self._harvest)

    def _nearest_node(self):
        frame = self.ctx.frame()
        if frame is None:
            return None
        h, w = frame.shape[:2]
        center = (w // 2, h // 2)
        best = None
        for tpl in self.templates:
            for m in self.ctx.detector.find_all_templates(frame, tpl):
                d = (m.center[0] - center[0]) ** 2 + (m.center[1] - center[1]) ** 2
                if best is None or d < best[0]:
                    best = (d, m)
        # YOLO fallback (class names like "ore", "tree").
        for m in self.ctx.detector.detect_objects(frame) if frame is not None else []:
            d = (m.center[0] - center[0]) ** 2 + (m.center[1] - center[1]) ** 2
            if best is None or d < best[0]:
                best = (d, m)
        return best[1] if best else None

    def _scan(self) -> Optional[str]:
        if self.should_stop():
            return None
        node = self._nearest_node()
        if node is None:
            log.debug("No node visible - panning camera")
            self.ctx.input.press_key("d")  # nudge camera/character to find nodes
            time.sleep(jittered(0.4, 0.9))
            return "scan"
        self._target = node
        return "approach"

    def _approach(self) -> Optional[str]:
        if self._target is None:
            return "scan"
        log.debug("Approaching node at %s", self._target.center)
        self.ctx.input.move_to(self._target.center)
        return "harvest"

    def _harvest(self) -> Optional[str]:
        log.debug("Harvesting")
        self.ctx.input.click(self._target.center, button="right")
        self.ctx.input.press_key(self.interact_key)
        time.sleep(jittered(2.0, 3.5))  # gather cast time
        self.on_success()
        self._target = None
        return "scan"
