"""A tiny, generic finite state machine used as the brain of every task.

Each state is a callable that returns the name of the next state (or None to
finish). This keeps task logic explicit and easy to reason about / unit test.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from src.utils.logger import get_logger

log = get_logger("fsm")

# A state handler receives no args and returns the next state name, or None.
StateHandler = Callable[[], Optional[str]]


class StateMachine:
    def __init__(self, name: str = "fsm") -> None:
        self.name = name
        self._states: Dict[str, StateHandler] = {}
        self._initial: Optional[str] = None
        self.current: Optional[str] = None
        self.running = False

    def add_state(self, name: str, handler: StateHandler, *, initial: bool = False) -> None:
        self._states[name] = handler
        if initial:
            self._initial = name

    def stop(self) -> None:
        self.running = False

    def run(self) -> None:
        if self._initial is None:
            raise RuntimeError(f"State machine '{self.name}' has no initial state")
        self.current = self._initial
        self.running = True
        log.debug("[%s] starting in state '%s'", self.name, self.current)

        while self.running and self.current is not None:
            handler = self._states.get(self.current)
            if handler is None:
                raise RuntimeError(f"Unknown state '{self.current}' in '{self.name}'")
            next_state = handler()
            if next_state != self.current:
                log.debug("[%s] %s -> %s", self.name, self.current, next_state)
            self.current = next_state

        self.running = False
        log.debug("[%s] finished", self.name)
