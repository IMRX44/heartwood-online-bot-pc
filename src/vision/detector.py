"""Perception: template matching, OCR, and optional YOLO object detection.

`Detector` is the bot's eyes. Tasks ask it questions like "where is the bobber?"
or "what's my HP%?" without caring whether the answer comes from a template,
OCR, or a neural net.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from src.core.config import VisionConfig
from src.utils.logger import get_logger

log = get_logger("vision.detector")

try:
    import cv2
    _HAS_CV2 = True
except Exception:  # pragma: no cover
    _HAS_CV2 = False

try:
    import pytesseract
    _HAS_OCR = True
except Exception:  # pragma: no cover
    _HAS_OCR = False


@dataclass
class Match:
    name: str
    center: Tuple[int, int]
    confidence: float
    box: Tuple[int, int, int, int]  # x, y, w, h


class Detector:
    def __init__(self, cfg: VisionConfig) -> None:
        self.cfg = cfg
        self._templates: dict[str, np.ndarray] = {}
        self._yolo = None
        if _HAS_CV2:
            self._load_templates()
        if cfg.yolo_model:
            self._load_yolo(cfg.yolo_model)

    # --- templates ------------------------------------------------------
    def _load_templates(self) -> None:
        tdir = Path(self.cfg.template_dir)
        if not tdir.exists():
            log.warning("Template dir %s missing - add reference images", tdir)
            return
        for img in tdir.glob("*.png"):
            tpl = cv2.imread(str(img))
            if tpl is not None:
                self._templates[img.name] = tpl
        log.info("Loaded %d templates", len(self._templates))

    def find_template(
        self, frame: np.ndarray, template_name: str,
        threshold: Optional[float] = None,
    ) -> Optional[Match]:
        """Return the best match for a template, or None below threshold."""
        if not _HAS_CV2 or template_name not in self._templates:
            return None
        tpl = self._templates[template_name]
        threshold = threshold if threshold is not None else self.cfg.match_threshold
        res = cv2.matchTemplate(frame, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < threshold:
            return None
        h, w = tpl.shape[:2]
        cx, cy = max_loc[0] + w // 2, max_loc[1] + h // 2
        return Match(template_name, (cx, cy), float(max_val), (max_loc[0], max_loc[1], w, h))

    def find_all_templates(
        self, frame: np.ndarray, template_name: str,
        threshold: Optional[float] = None,
    ) -> List[Match]:
        """Find every occurrence of a template (e.g. all ore nodes)."""
        if not _HAS_CV2 or template_name not in self._templates:
            return []
        tpl = self._templates[template_name]
        threshold = threshold if threshold is not None else self.cfg.match_threshold
        res = cv2.matchTemplate(frame, tpl, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= threshold)
        h, w = tpl.shape[:2]
        matches = [
            Match(template_name, (x + w // 2, y + h // 2), float(res[y, x]), (x, y, w, h))
            for x, y in zip(xs, ys)
        ]
        return _nms(matches)

    # --- OCR ------------------------------------------------------------
    def read_text(self, frame: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        if not (_HAS_OCR and self.cfg.ocr_enabled):
            return ""
        if region:
            x, y, w, h = region
            frame = frame[y:y + h, x:x + w]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if _HAS_CV2 else frame
        return pytesseract.image_to_string(gray).strip()

    def read_number(self, frame: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[int]:
        text = self.read_text(frame, region)
        digits = re.sub(r"[^0-9]", "", text)
        return int(digits) if digits else None

    # --- YOLO -----------------------------------------------------------
    def _load_yolo(self, model_path: str) -> None:
        try:
            from ultralytics import YOLO
            self._yolo = YOLO(model_path)
            log.info("Loaded YOLO model %s", model_path)
        except Exception as exc:  # pragma: no cover
            log.warning("Failed to load YOLO model: %s", exc)

    def detect_objects(self, frame: np.ndarray, conf: float = 0.5) -> List[Match]:
        if self._yolo is None:
            return []
        results = self._yolo(frame, conf=conf, verbose=False)
        matches: List[Match] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                name = r.names[int(box.cls[0])]
                matches.append(
                    Match(name, ((x1 + x2) // 2, (y1 + y2) // 2),
                          float(box.conf[0]), (x1, y1, x2 - x1, y2 - y1))
                )
        return matches


def _nms(matches: List[Match], min_dist: int = 20) -> List[Match]:
    """Crude non-max suppression: drop near-duplicate matches."""
    kept: List[Match] = []
    for m in sorted(matches, key=lambda x: -x.confidence):
        if all((m.center[0] - k.center[0]) ** 2 + (m.center[1] - k.center[1]) ** 2 > min_dist**2
               for k in kept):
            kept.append(m)
    return kept
