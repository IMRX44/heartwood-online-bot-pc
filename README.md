# Heartwood Online Bot

A modular automation framework for **Heartwood Online** (Steam App `2180600`).

Built as a portfolio project to demonstrate **Computer Vision**, **memory
reverse-engineering**, **network packet analysis**, and **human-like input
automation** working together behind a clean task/state-machine architecture.

> ⚠️ **Disclaimer.** This is an educational / portfolio project. Automating
> online games usually violates their Terms of Service and can get accounts
> banned. Use it only against your own test account, and at your own risk.

---

## What it does

Give it a high-level command and it executes:

```
> fish until 100
> gather ore for 30m
> farm mobs at goblin_camp
> craft iron_bar x50
```

It decides *how* using three independent perception backends that can be mixed
and matched:

| Backend          | Tech            | Used for                                  |
|------------------|-----------------|-------------------------------------------|
| **Vision**       | OpenCV + YOLO + Tesseract OCR | reading the screen (bobbers, mobs, HP bars, item counts) |
| **Memory**       | `pymem` (ReadProcessMemory) | exact player coords, HP/MP, inventory     |
| **Network**      | `scapy`         | passive packet sniffing for game events   |

…and acts through a **human-like input** layer (Bézier mouse paths, randomized
timing) driven by a **behavior state machine**.

## Architecture

```
main.py
  └── core/Bot ............ orchestrator: loads config, runs the state machine
        ├── vision/ ....... screen capture, template match, OCR, ML detection
        ├── memory/ ....... process attach + typed memory reads
        ├── network/ ...... packet sniffer + protocol parser
        ├── input/ ........ humanized keyboard + mouse controller
        ├── navigation/ ... A* pathfinding on the world map
        ├── tasks/ ........ Fishing / Gathering / Combat / Crafting
        └── commands/ ..... parse user commands into task queues
```

Each `tasks/*` task is a self-contained state machine that pulls perception
from whichever backend(s) are enabled in `config/config.yaml`, so you can run
pure-vision (works on any client) or memory-assisted (faster, more reliable).

## Quick start

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python main.py --task fish --count 100
# or interactive:
python main.py
> fish until 100
```

## Status / roadmap

This repo ships the **framework + non-game-specific implementations** (input,
vision pipeline, state machine, task engine, command parser, config, logging).
The game-specific bits below must be calibrated with the client running:

- [ ] Capture template images into `assets/templates/`
- [ ] Train / wire a YOLO model for mobs & resources
- [ ] Map memory offsets in `memory/offsets.py` (via Cheat Engine)
- [ ] Reverse the packet schema in `network/parser.py`

See [`docs/CALIBRATION.md`](docs/CALIBRATION.md) for how to fill these in.
