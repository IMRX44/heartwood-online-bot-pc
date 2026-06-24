"""Background worker so running a task never freezes the UI.

A TaskWorker runs one task on a QThread and emits signals for progress and
completion. A QtLogHandler bridges the logging module into a Qt signal so the
dashboard can show a live log.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class TaskWorker(QThread):
    finished_task = pyqtSignal(int)        # emits completed count
    error = pyqtSignal(str)

    def __init__(self, bot, task_name: str, kwargs: dict) -> None:
        super().__init__()
        self.bot = bot
        self.task_name = task_name
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            self.bot.run_task(self.task_name, **self.kwargs)
            task = getattr(self.bot, "_current_task", None)
            self.finished_task.emit(task.completed if task else 0)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            self.error.emit(str(exc))


class QtLogHandler(logging.Handler, QObject):
    """Logging handler that re-emits records as a Qt signal."""
    record = pyqtSignal(str, str)  # (levelname, message)

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.record.emit(record.levelname, self.format(record))
        except Exception:
            pass
