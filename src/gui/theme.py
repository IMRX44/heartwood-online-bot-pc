"""Dark theme stylesheet for the dashboard (Heartwood-inspired palette)."""

# Palette
BG = "#0f1419"
BG_ALT = "#161b22"
PANEL = "#1c2430"
BORDER = "#2a3441"
TEXT = "#c9d1d9"
TEXT_DIM = "#7d8590"
ACCENT = "#e0a458"      # warm "heartwood" amber
ACCENT_HOVER = "#f0b468"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Consolas", sans-serif;
    font-size: 13px;
}}
QMainWindow {{ background-color: {BG}; }}

QFrame#Panel {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QLabel#Title {{
    color: {ACCENT};
    font-size: 22px;
    font-weight: bold;
}}
QLabel#SubTitle {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#PanelHeader {{
    color: {ACCENT};
    font-size: 13px;
    font-weight: bold;
    padding: 2px 0;
}}
QLabel#StatValue {{ color: {TEXT}; font-size: 26px; font-weight: bold; }}
QLabel#StatLabel {{ color: {TEXT_DIM}; font-size: 11px; }}

QPushButton {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton:pressed {{ background-color: {PANEL}; }}
QPushButton#Primary {{
    background-color: {ACCENT};
    color: {BG};
    font-weight: bold;
    border: none;
}}
QPushButton#Primary:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#Danger {{ background-color: {RED}; color: white; border: none; font-weight: bold; }}
QPushButton#Danger:hover {{ background-color: #ff6359; }}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}

QTextEdit#Log {{
    background-color: #0a0e12;
    border: 1px solid {BORDER};
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}}

QProgressBar {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    text-align: center;
    height: 18px;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}

QLabel#Preview {{
    background-color: #000;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
"""
