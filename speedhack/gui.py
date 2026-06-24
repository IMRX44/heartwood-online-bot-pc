"""Standalone Speed Hack GUI (PyQt6).

Run: python speedhack/gui.py

Layout:
  ┌────────────────────────────────────────────────┐
  │  ⚡ HEARTWOOD SPEED HACK   ● DISCONNECTED       │
  ├────────────────────────────────────────────────┤
  │  BASE   │  CURRENT (mem)  │  TARGET (hacked)   │
  │  5.00   │  5.003          │  10.000            │
  ├────────────────────────────────────────────────┤
  │  Multiplier  ━━━━━━━━━━━━━━━━━━━━━  2.0 ×     │
  │  [1×]  [1.5×]  [2×]  [3×]  [5×]               │
  │  [🔗 ATTACH]  [▶ ENABLE]  [■ DISABLE]          │
  ├────────────────────────────────────────────────┤
  │  Manual address  [0x________]  base [5.0] [OK] │
  ├────────────────────────────────────────────────┤
  │  Hotkeys: F1 toggle · F12 panic                │
  └────────────────────────────────────────────────┘
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPushButton, QSlider, QVBoxLayout,
    QWidget,
)

from speedhack.src.hotkey import HotkeyManager
from speedhack.src.speed import SpeedHack

# ── Palette ────────────────────────────────────────────────────────────────
BG      = "#0f1419"
PANEL   = "#1c2430"
BORDER  = "#2a3441"
TEXT    = "#c9d1d9"
DIM     = "#7d8590"
AMBER   = "#e0a458"
GREEN   = "#3fb950"
RED     = "#f85149"

SS = f"""
QWidget {{ background:{BG}; color:{TEXT}; font-family:"Segoe UI",sans-serif; font-size:13px; }}
QFrame#P {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:10px; }}
QPushButton {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:7px; padding:7px 14px; }}
QPushButton:hover {{ border-color:{AMBER}; color:{AMBER}; }}
QPushButton#ok {{ background:{AMBER}; color:#000; font-weight:bold; border:none; }}
QPushButton#ok:hover {{ background:#f0b468; }}
QPushButton#bad {{ background:{RED}; color:#fff; border:none; font-weight:bold; }}
QLineEdit,QDoubleSpinBox,QSlider {{ background:#161b22; border:1px solid {BORDER}; border-radius:6px; padding:5px; }}
QLineEdit:focus {{ border-color:{AMBER}; }}
QLabel#val {{ color:{TEXT}; font-size:28px; font-weight:bold; }}
QLabel#cap {{ color:{DIM}; font-size:11px; }}
QLabel#hdr {{ color:{AMBER}; font-size:13px; font-weight:bold; }}
"""


def _panel() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame(); f.setObjectName("P")
    l = QVBoxLayout(f); l.setContentsMargins(14, 12, 14, 12)
    return f, l


def _card(label: str) -> tuple[QLabel, QFrame]:
    v = QLabel("—"); v.setObjectName("val")
    c = QLabel(label); c.setObjectName("cap")
    lay = QVBoxLayout(); lay.addWidget(v); lay.addWidget(c)
    f = QFrame(); f.setObjectName("P"); f.setLayout(lay)
    f.layout().setContentsMargins(12, 8, 12, 8)
    return v, f


class SpeedWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.hack   = SpeedHack()
        self.hotkey = HotkeyManager()
        self._build()
        self.hotkey.register(self._toggle, self._panic)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(200)

    # ── build ──────────────────────────────────────────────────────────────
    def _build(self) -> None:
        self.setWindowTitle("⚡ Heartwood Speed Hack")
        self.setStyleSheet(SS)
        self.setFixedWidth(520)

        root = QWidget(); self.setCentralWidget(root)
        lay  = QVBoxLayout(root)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(self._header())
        lay.addWidget(self._monitor())
        lay.addWidget(self._controls())
        lay.addWidget(self._manual_addr())
        lay.addWidget(self._hotkey_bar())

    def _header(self) -> QFrame:
        f, l = _panel()
        row  = QHBoxLayout()
        title = QLabel("⚡  HEARTWOOD SPEED HACK")
        title.setStyleSheet(f"color:{AMBER}; font-size:18px; font-weight:bold;")
        self._dot   = QLabel("●")
        self._dot.setStyleSheet(f"color:{DIM}; font-size:18px;")
        self._status = QLabel("DISCONNECTED")
        self._status.setStyleSheet(f"color:{DIM}; font-weight:bold;")
        row.addWidget(title); row.addStretch()
        row.addWidget(self._dot); row.addWidget(self._status)
        l.addLayout(row)
        return f

    def _monitor(self) -> QFrame:
        f, l = _panel()
        h = QLabel("SPEED MONITOR"); h.setObjectName("hdr")
        l.addWidget(h)
        g = QGridLayout()
        self._base_v, bw = _card("BASE SPEED")
        self._cur_v,  cw = _card("CURRENT (memory)")
        self._tgt_v,  tw = _card("TARGET (hacked)")
        g.addWidget(bw, 0, 0); g.addWidget(cw, 0, 1); g.addWidget(tw, 0, 2)
        l.addLayout(g)
        return f

    def _controls(self) -> QFrame:
        f, l = _panel()
        h = QLabel("MULTIPLIER"); h.setObjectName("hdr")
        l.addWidget(h)

        row = QHBoxLayout()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(10, 100); self._slider.setValue(20)
        self._slider.valueChanged.connect(lambda v: self._spin.setValue(v / 10))
        self._spin = QDoubleSpinBox()
        self._spin.setRange(1.0, 10.0); self._spin.setValue(2.0)
        self._spin.setSingleStep(0.1); self._spin.setSuffix(" ×")
        self._spin.valueChanged.connect(
            lambda v: (self._slider.blockSignals(True),
                       self._slider.setValue(int(v * 10)),
                       self._slider.blockSignals(False),
                       self._update_tgt()))
        row.addWidget(self._slider, 4); row.addWidget(self._spin, 1)
        l.addLayout(row)

        presets = QHBoxLayout()
        for lbl, val in [("1×", 1.0), ("1.5×", 1.5), ("2×", 2.0), ("3×", 3.0), ("5×", 5.0)]:
            b = QPushButton(lbl); b.setFixedWidth(56)
            b.clicked.connect(lambda _, v=val: self._spin.setValue(v))
            presets.addWidget(b)
        presets.addStretch()
        l.addLayout(presets)

        btns = QHBoxLayout()
        att = QPushButton("🔗  ATTACH"); att.setObjectName("ok"); att.clicked.connect(self._attach)
        ena = QPushButton("▶  ENABLE");  ena.clicked.connect(self._enable)
        dis = QPushButton("■  DISABLE"); dis.clicked.connect(self._disable)
        btns.addWidget(att); btns.addWidget(ena); btns.addWidget(dis)
        l.addLayout(btns)
        return f

    def _manual_addr(self) -> QFrame:
        f, l = _panel()
        h = QLabel("MANUAL ADDRESS OVERRIDE (Cheat Engine)"); h.setObjectName("hdr")
        l.addWidget(h)
        row = QHBoxLayout()
        self._addr_in  = QLineEdit(); self._addr_in.setPlaceholderText("0x1A2B3C4D")
        self._base_in  = QDoubleSpinBox()
        self._base_in.setRange(0.1, 1000); self._base_in.setValue(5.0); self._base_in.setSuffix(" base")
        ok = QPushButton("Apply"); ok.setObjectName("ok"); ok.setFixedWidth(64)
        ok.clicked.connect(self._apply_addr)
        row.addWidget(self._addr_in, 3); row.addWidget(self._base_in, 1); row.addWidget(ok)
        l.addLayout(row)
        return f

    def _hotkey_bar(self) -> QFrame:
        f, l = _panel()
        lbl = QLabel("Hotkeys:  <b>F1</b> toggle speed hack   ·   <b>F12</b> panic / disable")
        lbl.setStyleSheet(f"color:{DIM}; font-size:11px;")
        l.addWidget(lbl)
        return f

    # ── actions ────────────────────────────────────────────────────────────
    def _attach(self) -> None:
        self._set_status("ATTACHING…", DIM)
        if self.hack.attach():
            self._set_status("ATTACHED", GREEN)
            self._base_v.setText(f"{self.hack._base_speed:.2f}")
            self._update_tgt()
        else:
            self._set_status("ATTACH FAILED", RED)

    def _enable(self) -> None:
        self.hack.multiplier = self._spin.value()
        if self.hack.enable():
            self._set_status("ACTIVE ●", GREEN)
        else:
            self._set_status("ENABLE FAILED — attach first", RED)

    def _disable(self) -> None:
        self.hack.disable()
        self._set_status("ATTACHED (disabled)", GREEN)

    def _toggle(self) -> None:
        if self.hack.is_active:
            self._disable()
        else:
            self._enable()

    def _panic(self) -> None:
        self.hack.disable()
        self._set_status("PANIC — disabled", RED)

    def _apply_addr(self) -> None:
        try:
            addr = int(self._addr_in.text().strip(), 16)
        except ValueError:
            self._set_status("Bad address", RED)
            return
        self.hack.set_address(addr, self._base_in.value())
        self._base_v.setText(f"{self._base_in.value():.2f}")
        self._set_status("MANUAL ADDRESS SET", GREEN)

    def _update_tgt(self) -> None:
        if self.hack._base_speed:
            self._tgt_v.setText(f"{self.hack._base_speed * self._spin.value():.3f}")
        if self.hack.is_active:
            self.hack.multiplier = self._spin.value()

    def _set_status(self, text: str, color: str) -> None:
        self._dot.setStyleSheet(f"color:{color}; font-size:18px;")
        self._status.setStyleSheet(f"color:{color}; font-weight:bold;")
        self._status.setText(text)

    # ── live refresh ────────────────────────────────────────────────────────
    def _refresh(self) -> None:
        spd = self.hack.current_speed()
        if spd is not None:
            self._cur_v.setText(f"{spd:.3f}")

    def closeEvent(self, e) -> None:  # noqa: N802
        self.hack.disable(); self.hotkey.stop(); super().closeEvent(e)


def main() -> int:
    app = QApplication(sys.argv)
    w   = SpeedWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
