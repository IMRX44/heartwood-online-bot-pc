"""Launch the Heartwood Online Bot dashboard.

    python gui.py
"""
from __future__ import annotations

import sys

from src.core.config import Config
from src.utils.logger import setup_logging


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from src.gui.dashboard import Dashboard

    config = Config.load()
    setup_logging(config.logging.level, config.logging.file)

    app = QApplication(sys.argv)
    window = Dashboard(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
