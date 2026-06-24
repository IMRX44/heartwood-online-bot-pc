"""Task base class and the shared context tasks operate on.

A Task wires perception backends + input into a StateMachine. Subclasses build
their own states. `TaskContext` is the bundle of capabilities every task gets.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.core.state_machine import StateMachine
from src.input.controller import InputController
from src.utils.logger import get_logger

log = get_logger("task")


@dataclass
class TaskContext:
    """Everything a task needs, injected by the Bot orchestrator."""
    config: object
    input: InputController
    screen: object                     # ScreenCapture
    detector: object                   # Detector
    memory: Optional[object] = None    # MemoryReader (if enabled)
    sniffer: Optional[object] = None   # PacketSniffer (if enabled)

    def frame(self) -> Optional[np.ndarray]:
        return self.screen.grab()


class Task:
    name: str = "task"

    def __init__(self, ctx: TaskContext, *, count: Optional[int] = None,
                 duration: Optional[float] = None, **kwargs) -> None:
        self.ctx = ctx
        self.target_count = count          # stop after N successes
        self.duration = duration           # stop after N seconds
        self.kwargs = kwargs
        self.completed = 0
        self._start_time = 0.0
        self.fsm = StateMachine(self.name)
        self.build()

    def build(self) -> None:
        """Subclasses register their states here."""
        raise NotImplementedError

    # --- stop conditions ------------------------------------------------
    def should_stop(self) -> bool:
        if self.target_count is not None and self.completed >= self.target_count:
            log.info("[%s] reached target count %d", self.name, self.target_count)
            return True
        if self.duration is not None and (time.time() - self._start_time) >= self.duration:
            log.info("[%s] reached duration %.0fs", self.name, self.duration)
            return True
        return False

    def on_success(self) -> None:
        self.completed += 1
        log.info("[%s] success #%d", self.name, self.completed)

    def run(self) -> None:
        self._start_time = time.time()
        log.info("[%s] starting (count=%s, duration=%s)",
                 self.name, self.target_count, self.duration)
        self.fsm.run()
        log.info("[%s] done - %d completed", self.name, self.completed)

    def stop(self) -> None:
        self.fsm.stop()
