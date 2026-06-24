"""The Bot orchestrator: wires backends together and runs tasks.

Responsibilities:
  - load config + set up backends (vision always, memory/network if enabled)
  - locate the game window
  - register a global panic hotkey (emergency stop)
  - build a TaskContext and run requested tasks
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from src.core.config import Config
from src.input.controller import InputController
from src.tasks import TASK_REGISTRY
from src.tasks.base import TaskContext
from src.utils.logger import get_logger
from src.vision.detector import Detector
from src.vision.screen import ScreenCapture

log = get_logger("bot")


class Bot:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.input = InputController(config.input)
        self.screen = ScreenCapture()
        self.detector = Detector(config.vision)
        self.memory = None
        self.sniffer = None
        self._current_task = None
        self._panic = threading.Event()

        self._init_backends()
        self._locate_window()
        self._register_panic_key()

    # --- setup ----------------------------------------------------------
    def _init_backends(self) -> None:
        if self.config.backends.memory:
            from src.memory.reader import MemoryReader
            self.memory = MemoryReader(self.config.game.process_name)
            if not self.memory.attach():
                self.memory = None

        if self.config.backends.network:
            from src.network.sniffer import PacketSniffer
            self.sniffer = PacketSniffer(on_event=self._on_packet)
            self.sniffer.start()

    def _on_packet(self, event) -> None:
        log.debug("Packet event: %s", event.name)

    def _locate_window(self) -> None:
        """Find the game window and scope screen capture to it."""
        try:
            import pygetwindow as gw  # type: ignore
            wins = gw.getWindowsWithTitle(self.config.game.window_title)
            if wins:
                w = wins[0]
                self.screen.set_region((w.left, w.top, w.width, w.height))
                log.info("Game window at (%d,%d) %dx%d", w.left, w.top, w.width, w.height)
                return
        except Exception:
            pass
        log.warning("Game window not found - capturing full screen")

    def _register_panic_key(self) -> None:
        """Global hotkey to abort everything immediately."""
        try:
            from pynput import keyboard
            key = self.config.behavior.panic_key

            def on_press(k):
                try:
                    if getattr(k, "name", None) == key or str(k).strip("'") == key:
                        log.warning("PANIC KEY pressed - stopping")
                        self.stop()
                except Exception:
                    pass

            listener = keyboard.Listener(on_press=on_press)
            listener.daemon = True
            listener.start()
            log.info("Panic key '%s' armed", key)
        except Exception as exc:  # pragma: no cover
            log.debug("Could not register panic key: %s", exc)

    # --- running --------------------------------------------------------
    def _make_context(self) -> TaskContext:
        return TaskContext(
            config=self.config,
            input=self.input,
            screen=self.screen,
            detector=self.detector,
            memory=self.memory,
            sniffer=self.sniffer,
        )

    def run_task(self, task_name: str, **kwargs: Any) -> None:
        if self._panic.is_set():
            log.warning("Panic flag set - refusing to start task")
            return
        task_cls = TASK_REGISTRY.get(task_name)
        if task_cls is None:
            log.error("Unknown task '%s'. Known: %s",
                      task_name, ", ".join(TASK_REGISTRY))
            return
        ctx = self._make_context()
        self._current_task = task_cls(ctx, **kwargs)
        try:
            self._current_task.run()
        except KeyboardInterrupt:
            log.info("Interrupted by user")
            self.stop()

    def run_command(self, text: str) -> None:
        from src.commands.interpreter import parse
        cmd = parse(text)
        if cmd is None:
            log.error("Could not understand command: %r", text)
            return
        log.info("Parsed command: task=%s kwargs=%s", cmd.task, cmd.kwargs)
        self.run_task(cmd.task, **cmd.kwargs)

    def stop(self) -> None:
        self._panic.set()
        if self._current_task is not None:
            self._current_task.stop()
        if self.sniffer is not None:
            self.sniffer.stop()
