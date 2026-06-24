"""Heartwood Online Bot - entry point.

Usage:
    python main.py                       # interactive command shell
    python main.py --task fish --count 100
    python main.py --command "gather ore for 30m"
"""
from __future__ import annotations

import argparse
import sys

from src.core.bot import Bot
from src.core.config import Config
from src.utils.logger import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Heartwood Online Bot")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--task", help="task name: fish, gather, farm, craft")
    parser.add_argument("--count", type=int, help="stop after N successes")
    parser.add_argument("--duration", type=float, help="stop after N seconds")
    parser.add_argument("--command", help='natural command, e.g. "fish until 100"')
    args = parser.parse_args(argv)

    config = Config.load(args.config)
    log = setup_logging(config.logging.level, config.logging.file)
    log.info("Heartwood Online Bot starting")

    bot = Bot(config)

    if args.command:
        bot.run_command(args.command)
        return 0

    if args.task:
        kwargs = {}
        if args.count is not None:
            kwargs["count"] = args.count
        if args.duration is not None:
            kwargs["duration"] = args.duration
        bot.run_task(args.task, **kwargs)
        return 0

    # Interactive shell.
    log.info("Interactive mode. Type a command (e.g. 'fish until 100') or 'quit'.")
    try:
        while True:
            text = input("> ").strip()
            if text.lower() in {"quit", "exit", "q"}:
                break
            if text:
                bot.run_command(text)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        bot.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
