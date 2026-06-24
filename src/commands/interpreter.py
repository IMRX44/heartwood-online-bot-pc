"""Natural-ish command parser.

Turns simple English commands into a (task_name, kwargs) the Bot can run:

    "fish until 100"          -> ("fish",  {count: 100})
    "gather ore for 30m"      -> ("gather",{templates: ["ore_node.png"], duration: 1800})
    "farm mobs at goblin_camp"-> ("farm",  {location: "goblin_camp"})
    "craft iron_bar x50"      -> ("craft", {recipe: "iron_bar", count: 50})

Deliberately rule-based and transparent (easy to demo / extend) rather than an
LLM black box.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.tasks import TASK_REGISTRY


@dataclass
class Command:
    task: str
    kwargs: Dict[str, Any] = field(default_factory=dict)


_DURATION_RE = re.compile(r"for\s+(\d+)\s*(s|m|h|sec|min|hour)?", re.I)
_COUNT_RE = re.compile(r"(?:until|x|times?|count)\s*(\d+)|(\d+)\s*(?:times)", re.I)
_AT_RE = re.compile(r"\bat\s+(\w+)", re.I)

_RESOURCE_ALIASES = {
    "ore": "ore_node.png", "mining": "ore_node.png",
    "wood": "tree.png", "tree": "tree.png", "woodcutting": "tree.png",
    "herb": "herb.png", "herbs": "herb.png",
}


def parse(text: str) -> Optional[Command]:
    text = text.strip().lower()
    if not text:
        return None

    verb = text.split()[0]
    if verb not in TASK_REGISTRY:
        return None

    kwargs: Dict[str, Any] = {}

    # duration: "for 30m"
    dm = _DURATION_RE.search(text)
    if dm:
        val = int(dm.group(1))
        unit = (dm.group(2) or "s")[0]
        kwargs["duration"] = val * {"s": 1, "m": 60, "h": 3600}.get(unit, 1)

    # count: "until 100", "x50"
    cm = _COUNT_RE.search(text)
    if cm:
        num = cm.group(1) or cm.group(2)
        if num:
            kwargs["count"] = int(num)

    # location: "at goblin_camp"
    am = _AT_RE.search(text)
    if am:
        kwargs["location"] = am.group(1)

    # gathering resource type
    if verb == "gather":
        for word in text.split():
            if word in _RESOURCE_ALIASES:
                kwargs["templates"] = [_RESOURCE_ALIASES[word]]
                break

    # crafting recipe: "craft iron_bar x50"
    if verb == "craft":
        tokens = text.split()
        if len(tokens) > 1 and not tokens[1].isdigit():
            kwargs["recipe"] = re.sub(r"x?\d+$", "", tokens[1]).strip("_")

    return Command(task=verb, kwargs=kwargs)
