"""Heartwood Online Bot - PyQt6 dashboard.

Layout:
  +-----------------------------------------------------------+
  |  HEARTWOOD BOT          [vision][memory][network] status  |
  +-----------------------------------------------------------+
  |  [BOT]  [SPEED HACK]   <- tab bar                         |
  +----------------------+------------------------------------+
  |  Live screen preview  |  Control panel (bot or cheats)    |
  +----------------------+------------------------------------+
  |  Live log                                                 |
  +-----------------------------------------------------------+
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QSpinBox, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from src.commands.interpreter import parse
from src.core.bot import Bot
from src.core.config import Config
from src.gui import theme
from src.gui.speed_tab import SpeedTab
from src.gui.worker import QtLogHandler, TaskWorker
from src.tasks import TASK_REGISTRY
from src.utils.logger import get_logger

log = get_logger("gui")

try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


def _panel(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    if title:
        header = QLabel(title)
        header.setObjectName("PanelHeader")
        layout.addWidget(header)
    return frame, layout


class StatCard(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("Panel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        self.value = QLabel("0")
        self.value.setObjectName("StatValue")
        cap = QLabel(label)
        cap.setObjectName("StatLabel")
        lay.addWidget(self.value)
        lay.addWidget(cap)

    def set(self, text: str) -> None:
        self.value.setText(text)


class Dashboard(QMainWindow):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.bot = Bot(config)
        self.worker: Optional[TaskWorker] = None
        self._run_start = 0.0

        self.setWindowTitle("Heartwood Online Bot")
        self.resize(1180, 760)
        self.setStyleSheet(theme.STYLESHEET)
        self._build_ui()
        self._wire_logging()

        # Live preview + stats refresh loop.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(150)

    # --- UI construction ------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        outer.addLayout(self._build_header())

        # Tab bar: BOT | SPEED HACK
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: {theme.BG_ALT}; border: 1px solid {theme.BORDER};
                border-bottom: none; padding: 8px 20px; border-radius: 6px 6px 0 0;
                color: {theme.TEXT_DIM};
            }}
            QTabBar::tab:selected {{ background: {theme.PANEL}; color: {theme.ACCENT}; font-weight: bold; }}
            QTabWidget::pane {{ border: 1px solid {theme.BORDER}; border-radius: 0 8px 8px 8px; }}
        """)

        # Tab 0: Bot automation
        bot_tab = QWidget()
        bot_lay = QVBoxLayout(bot_tab)
        bot_lay.setContentsMargins(0, 8, 0, 0)
        mid = QHBoxLayout()
        mid.setSpacing(12)
        mid.addWidget(self._build_preview(), stretch=3)
        mid.addWidget(self._build_controls(), stretch=2)
        bot_lay.addLayout(mid)
        self.tabs.addTab(bot_tab, "⚙  BOT")

        # Tab 1: Speed Hack
        self.speed_tab = SpeedTab(self.config.game.process_name)
        self.tabs.addTab(self.speed_tab, "⚡  SPEED HACK")

        outer.addWidget(self.tabs, stretch=3)
        outer.addWidget(self._build_log(), stretch=2)

    def _build_header(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("⚔  HEARTWOOD BOT")
        title.setObjectName("Title")
        sub = QLabel("multi-backend automation dashboard")
        sub.setObjectName("SubTitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        bar.addLayout(title_box)
        bar.addStretch()

        self.backend_labels = {}
        for name in ("vision", "memory", "network"):
            enabled = getattr(self.config.backends, name)
            lbl = QLabel(f"● {name}")
            color = theme.GREEN if enabled else theme.TEXT_DIM
            lbl.setStyleSheet(f"color: {color}; font-weight: bold; padding: 0 8px;")
            self.backend_labels[name] = lbl
            bar.addWidget(lbl)
        return bar

    def _build_preview(self) -> QFrame:
        frame, lay = _panel("LIVE PREVIEW")
        self.preview = QLabel("waiting for frames…")
        self.preview.setObjectName("Preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(560, 360)
        lay.addWidget(self.preview)
        return frame

    def _build_controls(self) -> QFrame:
        frame, lay = _panel("CONTROL")

        lay.addWidget(QLabel("Command"))
        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText('e.g. "fish until 100"  or  "gather ore for 30m"')
        self.cmd_input.returnPressed.connect(self._run_command)
        run_btn = QPushButton("Run")
        run_btn.setObjectName("Primary")
        run_btn.clicked.connect(self._run_command)
        cmd_row.addWidget(self.cmd_input)
        cmd_row.addWidget(run_btn)
        lay.addLayout(cmd_row)

        lay.addSpacing(6)
        lay.addWidget(QLabel("Or pick a task"))
        picker = QHBoxLayout()
        self.task_combo = QComboBox()
        self.task_combo.addItems(sorted(set(TASK_REGISTRY)))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 100000)
        self.count_spin.setPrefix("count ")
        self.count_spin.setSpecialValueText("count ∞")
        picker.addWidget(self.task_combo, stretch=2)
        picker.addWidget(self.count_spin, stretch=1)
        lay.addLayout(picker)

        lay.addSpacing(8)
        btns = QHBoxLayout()
        self.start_btn = QPushButton("▶  START")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self._start_task)
        self.stop_btn = QPushButton("■  STOP")
        self.stop_btn.clicked.connect(self._stop_task)
        self.panic_btn = QPushButton("⛔  PANIC")
        self.panic_btn.setObjectName("Danger")
        self.panic_btn.clicked.connect(self._panic)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addWidget(self.panic_btn)
        lay.addLayout(btns)

        lay.addSpacing(10)
        stats = QGridLayout()
        self.stat_status = StatCard("STATUS")
        self.stat_status.set("idle")
        self.stat_count = StatCard("COMPLETED")
        self.stat_runtime = StatCard("RUNTIME")
        self.stat_rate = StatCard("PER HOUR")
        stats.addWidget(self.stat_status, 0, 0)
        stats.addWidget(self.stat_count, 0, 1)
        stats.addWidget(self.stat_runtime, 1, 0)
        stats.addWidget(self.stat_rate, 1, 1)
        lay.addLayout(stats)
        lay.addStretch()
        return frame

    def _build_log(self) -> QFrame:
        frame, lay = _panel("LIVE LOG")
        self.log_view = QTextEdit()
        self.log_view.setObjectName("Log")
        self.log_view.setReadOnly(True)
        lay.addWidget(self.log_view)
        return frame

    # --- logging bridge -------------------------------------------------
    def _wire_logging(self) -> None:
        handler = QtLogHandler()
        handler.setFormatter(__import__("logging").Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
        handler.record.connect(self._append_log)
        __import__("logging").getLogger("heartwood").addHandler(handler)

    def _append_log(self, level: str, msg: str) -> None:
        color = {"ERROR": theme.RED, "WARNING": theme.ACCENT,
                 "INFO": theme.TEXT, "DEBUG": theme.TEXT_DIM}.get(level, theme.TEXT)
        self.log_view.append(f'<span style="color:{color}">{msg}</span>')

    # --- actions --------------------------------------------------------
    def _start_worker(self, task: str, kwargs: dict) -> None:
        if self.worker and self.worker.isRunning():
            log.warning("A task is already running")
            return
        self.bot._panic.clear()
        self._run_start = time.time()
        self.stat_status.set("running")
        self.worker = TaskWorker(self.bot, task, kwargs)
        self.worker.finished_task.connect(self._on_task_done)
        self.worker.error.connect(lambda e: log.error("Task error: %s", e))
        self.worker.start()

    def _run_command(self) -> None:
        text = self.cmd_input.text().strip()
        if not text:
            return
        cmd = parse(text)
        if cmd is None:
            log.error("Could not understand: %r", text)
            return
        self._start_worker(cmd.task, cmd.kwargs)

    def _start_task(self) -> None:
        kwargs: dict = {}
        if self.count_spin.value() > 0:
            kwargs["count"] = self.count_spin.value()
        self._start_worker(self.task_combo.currentText(), kwargs)

    def _stop_task(self) -> None:
        self.bot.stop()
        self.stat_status.set("stopping")

    def _panic(self) -> None:
        self.bot.stop()
        self.stat_status.set("PANIC")
        log.warning("PANIC pressed from dashboard")

    def _on_task_done(self, completed: int) -> None:
        self.stat_status.set("idle")
        log.info("Task finished: %d completed", completed)

    # --- live refresh ---------------------------------------------------
    def _tick(self) -> None:
        self._update_preview()
        self._update_stats()

    def _update_preview(self) -> None:
        frame = self.bot.screen.grab()
        if frame is None:
            return
        frame = self._draw_overlays(frame)
        if _HAS_CV2:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        img = QImage(frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.preview.width(), self.preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(pix)

    def _draw_overlays(self, frame: np.ndarray) -> np.ndarray:
        """Draw detection boxes from any loaded YOLO model onto the preview."""
        if not _HAS_CV2:
            return frame
        try:
            for m in self.bot.detector.detect_objects(frame):
                x, y, w, h = m.box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (88, 166, 255), 2)
                cv2.putText(frame, f"{m.name} {m.confidence:.2f}", (x, y - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (88, 166, 255), 1)
        except Exception:
            pass
        return frame

    def _update_stats(self) -> None:
        task = getattr(self.bot, "_current_task", None)
        running = bool(self.worker and self.worker.isRunning())
        completed = task.completed if task else 0
        self.stat_count.set(str(completed))
        if running:
            elapsed = time.time() - self._run_start
            mins, secs = divmod(int(elapsed), 60)
            self.stat_runtime.set(f"{mins:02d}:{secs:02d}")
            rate = completed / elapsed * 3600 if elapsed > 0 else 0
            self.stat_rate.set(f"{rate:.0f}")
        # Backend indicators reflect actual attachment state.
        if self.bot.memory is not None:
            self.backend_labels["memory"].setStyleSheet(
                f"color: {theme.GREEN}; font-weight: bold; padding: 0 8px;")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        self.bot.stop()
        super().closeEvent(event)
