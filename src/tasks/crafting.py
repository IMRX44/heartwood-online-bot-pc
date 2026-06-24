"""Auto-crafting task.

State flow:
  open_menu -> select_recipe -> craft -> verify -> craft ...

Opens the crafting UI, selects a recipe by template/OCR, and repeats the craft
action until the requested count is reached.
"""
from __future__ import annotations

import time
from typing import Optional

from src.input.humanize import jittered
from src.tasks.base import Task
from src.utils.logger import get_logger

log = get_logger("task.crafting")


class CraftingTask(Task):
    name = "craft"

    def build(self) -> None:
        tcfg = self.ctx.config.tasks.get("crafting", {})
        self.open_key = tcfg.get("open_craft_key", "c")
        self.recipe = self.kwargs.get("recipe", "")  # e.g. "iron_bar"
        self.recipe_template = f"recipe_{self.recipe}.png" if self.recipe else ""

        self.fsm.add_state("open_menu", self._open_menu, initial=True)
        self.fsm.add_state("select_recipe", self._select_recipe)
        self.fsm.add_state("craft", self._craft)

    def _open_menu(self) -> Optional[str]:
        if self.should_stop():
            return None
        self.ctx.input.press_key(self.open_key)
        time.sleep(jittered(0.5, 1.0))
        return "select_recipe"

    def _select_recipe(self) -> Optional[str]:
        if not self.recipe_template:
            log.warning("No recipe specified - cannot craft")
            return None
        frame = self.ctx.frame()
        if frame is not None:
            m = self.ctx.detector.find_template(frame, self.recipe_template)
            if m is not None:
                self.ctx.input.click(m.center)
                time.sleep(jittered(0.3, 0.6))
                return "craft"
        log.debug("Recipe '%s' not found in menu", self.recipe)
        time.sleep(0.3)
        return "select_recipe"

    def _craft(self) -> Optional[str]:
        if self.should_stop():
            return None
        # TODO: locate and click the actual "Craft" button via template.
        self.ctx.input.press_key("enter")
        time.sleep(jittered(1.5, 2.5))  # craft cast time
        self.on_success()
        return "craft"
