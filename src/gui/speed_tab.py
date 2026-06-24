"""Speed Hack control tab for the dashboard.

Shows:
  - current / hacked speed (live read from memory)
  - multiplier slider
  - ATTACH / ENABLE / DISABLE buttons
  - address override (manual hex input)
  - status indicator dot
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from src.cheat.speed_hack import SpeedHack
from src.gui import theme
from src.utils.logger import get_logger

log = get_logger("gui.speed")


def _panel(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Panel")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 12)
    if title:
        h = QLabel(title)
        h.setObjectName("PanelHeader")
        lay.addWidget(h)
    return frame, lay


class SpeedTab(QWidget):
    """Dropped into the dashboard as a tab widget."""

    def __init__(self, process_name: str = "Heartwood.exe") -> None:
        super().__init__()
        self.hack = SpeedHack(process_name)
        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(200)

    # --- layout ---------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        root.addWidget(self._build_status_row())
        root.addWidget(self._build_speed_panel())
        root.addWidget(self._build_controls())
        root.addWidget(self._build_address_panel())
        root.addStretch()

    def _build_status_row(self) -> QFrame:
        frame, lay = _panel()
        row = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 20px;")
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet(f"color: {theme.TEXT_DIM}; font-weight: bold;")
        row.addWidget(self.status_dot)
        row.addWidget(self.status_label)
        row.addStretch()

        self.attach_btn = QPushButton("🔗  ATTACH")
        self.attach_btn.setObjectName("Primary")
        self.attach_btn.clicked.connect(self._attach)
        row.addWidget(self.attach_btn)
        lay.addLayout(row)
        return frame

    def _build_speed_panel(self) -> QFrame:
        frame, lay = _panel("SPEED MONITOR")
        grid = QGridLayout()

        def card(label: str) -> QLabel:
            v = QLabel("—")
            v.setObjectName("StatValue")
            c = QLabel(label)
            c.setObjectName("StatLabel")
            sub = QVBoxLayout()
            sub.addWidget(v)
            sub.addWidget(c)
            w = QFrame()
            w.setObjectName("Panel")
            w.setLayout(sub)
            w.layout().setContentsMargins(12, 8, 12, 8)
            return v, w

        self.base_val, base_w   = card("BASE SPEED")
        self.cur_val, cur_w     = card("CURRENT (memory)")
        self.hacked_val, hack_w = card("TARGET (hacked)")
        grid.addWidget(base_w,   0, 0)
        grid.addWidget(cur_w,    0, 1)
        grid.addWidget(hack_w,   0, 2)
        lay.addLayout(grid)
        return frame

    def _build_controls(self) -> QFrame:
        frame, lay = _panel("MULTIPLIER")

        slider_row = QHBoxLayout()
        self.mult_slider = QSlider(Qt.Orientation.Horizontal)
        self.mult_slider.setRange(10, 100)  # 1.0× – 10.0×
        self.mult_slider.setValue(20)        # default 2.0×
        self.mult_slider.setTickInterval(10)
        self.mult_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.mult_slider.valueChanged.connect(self._slider_changed)

        self.mult_spin = QDoubleSpinBox()
        self.mult_spin.setRange(1.0, 10.0)
        self.mult_spin.setSingleStep(0.1)
        self.mult_spin.setDecimals(1)
        self.mult_spin.setSuffix(" ×")
        self.mult_spin.setValue(2.0)
        self.mult_spin.valueChanged.connect(self._spin_changed)

        slider_row.addWidget(self.mult_slider, stretch=4)
        slider_row.addWidget(self.mult_spin, stretch=1)
        lay.addLayout(slider_row)

        # Speed presets
        preset_row = QHBoxLayout()
        for label, val in [("1×", 1.0), ("1.5×", 1.5), ("2×", 2.0),
                            ("3×", 3.0), ("5×", 5.0)]:
            btn = QPushButton(label)
            btn.setFixedWidth(56)
            btn.clicked.connect(lambda _, v=val: self._set_multiplier(v))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        lay.addLayout(preset_row)

        # Enable / Disable
        btn_row = QHBoxLayout()
        self.enable_btn = QPushButton("▶  ENABLE")
        self.enable_btn.setObjectName("Primary")
        self.enable_btn.clicked.connect(self._enable)
        self.disable_btn = QPushButton("■  DISABLE")
        self.disable_btn.clicked.connect(self._disable)
        btn_row.addWidget(self.enable_btn)
        btn_row.addWidget(self.disable_btn)
        lay.addLayout(btn_row)
        return frame

    def _build_address_panel(self) -> QFrame:
        frame, lay = _panel("MANUAL ADDRESS OVERRIDE")
        note = QLabel(
            "Paste the hex address from Cheat Engine here to skip the AOB scan.\n"
            "Leave blank to use AOB scan on attach."
        )
        note.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        lay.addWidget(note)

        row = QHBoxLayout()
        self.addr_input = QLineEdit()
        self.addr_input.setPlaceholderText("e.g.  0x1A2B3C4D")

        self.base_speed_input = QDoubleSpinBox()
        self.base_speed_input.setRange(0.1, 1000.0)
        self.base_speed_input.setValue(5.0)
        self.base_speed_input.setSuffix(" base")
        self.base_speed_input.setToolTip("Original movement speed in-game")

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_manual_addr)

        row.addWidget(self.addr_input, stretch=3)
        row.addWidget(self.base_speed_input, stretch=1)
        row.addWidget(apply_btn)
        lay.addLayout(row)
        return frame

    # --- actions --------------------------------------------------------
    def _attach(self) -> None:
        self.status_label.setText("ATTACHING…")
        if self.hack.attach():
            self._set_status_ok("ATTACHED")
            self.base_val.setText(f"{self.hack._base_speed:.2f}")
            self.hacked_val.setText(f"{self.hack._base_speed * self.hack.multiplier:.2f}")
        else:
            self._set_status_err("ATTACH FAILED")

    def _enable(self) -> None:
        self.hack.multiplier = self.mult_spin.value()
        if self.hack.enable():
            self._set_status_ok("ACTIVE")
        else:
            self._set_status_err("ENABLE FAILED — attach first")

    def _disable(self) -> None:
        self.hack.disable()
        self._set_status_ok("ATTACHED (disabled)")

    def _apply_manual_addr(self) -> None:
        txt = self.addr_input.text().strip()
        if not txt:
            return
        try:
            addr = int(txt, 16)
        except ValueError:
            log.error("Invalid address: %r", txt)
            return
        base = self.base_speed_input.value()
        self.hack.set_address(addr, base)
        self.base_val.setText(f"{base:.2f}")
        self._set_status_ok("MANUAL ADDRESS SET")

    def _set_multiplier(self, val: float) -> None:
        self.mult_spin.setValue(val)
        self.mult_slider.setValue(int(val * 10))

    def _slider_changed(self, raw: int) -> None:
        self.mult_spin.blockSignals(True)
        self.mult_spin.setValue(raw / 10)
        self.mult_spin.blockSignals(False)
        self._update_hacked_display()

    def _spin_changed(self, val: float) -> None:
        self.mult_slider.blockSignals(True)
        self.mult_slider.setValue(int(val * 10))
        self.mult_slider.blockSignals(False)
        self._update_hacked_display()

    def _update_hacked_display(self) -> None:
        if self.hack._base_speed:
            t = self.hack._base_speed * self.mult_spin.value()
            self.hacked_val.setText(f"{t:.2f}")
        if self.hack.is_active:
            self.hack.multiplier = self.mult_spin.value()

    # --- status helpers -------------------------------------------------
    def _set_status_ok(self, text: str) -> None:
        self.status_dot.setStyleSheet(f"color: {theme.GREEN}; font-size: 20px;")
        self.status_label.setStyleSheet(f"color: {theme.GREEN}; font-weight: bold;")
        self.status_label.setText(text)

    def _set_status_err(self, text: str) -> None:
        self.status_dot.setStyleSheet(f"color: {theme.RED}; font-size: 20px;")
        self.status_label.setStyleSheet(f"color: {theme.RED}; font-weight: bold;")
        self.status_label.setText(text)

    # --- live refresh ---------------------------------------------------
    def _refresh(self) -> None:
        spd = self.hack.current_speed()
        if spd is not None:
            self.cur_val.setText(f"{spd:.3f}")
        if self.hack.is_active:
            self._set_status_ok("ACTIVE ●")
