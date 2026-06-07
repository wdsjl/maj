"""UI 区域定义与裁剪。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int

    def crop(self, image: np.ndarray) -> np.ndarray:
        x2 = min(self.x + self.width, image.shape[1])
        y2 = min(self.y + self.height, image.shape[0])
        return image[self.y:y2, self.x:x2]

    def slot_rects(self, count: int) -> list["Rect"]:
        """将区域均分为 count 个槽位。"""
        slot_w = self.width // count
        return [
            Rect(self.x + i * slot_w, self.y, slot_w, self.height)
            for i in range(count)
        ]


@dataclass
class RegionConfig:
    hand: Rect
    dora: Rect
    max_hand_slots: int

    @classmethod
    def from_config(cls, vision_cfg: dict[str, Any]) -> "RegionConfig":
        h = vision_cfg["hand"]
        d = vision_cfg["dora"]
        return cls(
            hand=Rect(h["x"], h["y"], h["width"], h["height"]),
            dora=Rect(d["x"], d["y"], d["width"], d["height"]),
            max_hand_slots=h.get("max_slots", 14),
        )


def detect_tile_in_slot(slot_bgr: np.ndarray, brightness_threshold: int = 40) -> bool:
    """检测槽位内是否有牌（基于亮度）。"""
    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    # 取牌面中央区域
    h, w = gray.shape
    cx1, cx2 = int(w * 0.25), int(w * 0.75)
    cy1, cy2 = int(h * 0.15), int(h * 0.85)
    region = gray[cy1:cy2, cx1:cx2]
    return float(np.mean(region)) > brightness_threshold
