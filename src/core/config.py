"""Typed configuration loaded from config/config.yaml via pydantic."""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field


class GameConfig(BaseModel):
    window_title: str = "Heartwood Online"
    process_name: str = "Heartwood.exe"


class BackendsConfig(BaseModel):
    vision: bool = True
    memory: bool = False
    network: bool = False


class VisionConfig(BaseModel):
    capture_fps: int = 10
    template_dir: str = "assets/templates"
    match_threshold: float = 0.82
    ocr_enabled: bool = True
    yolo_model: str = ""


class InputConfig(BaseModel):
    mouse_move_duration: List[float] = [0.15, 0.45]
    action_delay: List[float] = [0.08, 0.25]
    use_direct_input: bool = True


class BehaviorConfig(BaseModel):
    break_every: List[int] = [900, 1800]
    break_duration: List[int] = [30, 120]
    panic_key: str = "f12"


class DiscordConfig(BaseModel):
    enabled: bool = False
    token: str = ""
    channel_id: int = 0


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/bot.log"


class Config(BaseModel):
    game: GameConfig = Field(default_factory=GameConfig)
    backends: BackendsConfig = Field(default_factory=BackendsConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    tasks: dict = Field(default_factory=dict)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: str | Path = "config/config.yaml") -> "Config":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(**data)
