"""牌河区域定义与座位映射。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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
        x1 = max(0, self.x)
        y1 = max(0, self.y)
        return image[y1:y2, x1:x2]

    def slot_rects(self, count: int) -> list["Rect"]:
        slot_w = self.width // count
        return [
            Rect(self.x + i * slot_w, self.y, slot_w, self.height)
            for i in range(count)
        ]


class RiverOrientation(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class RiverLayout:
    """单个玩家的牌河布局。"""
    screen_pos: str  # self | right | across | left
    rect: Rect
    orientation: RiverOrientation
    rows: int
    cols: int
    tile_width: int
    tile_height: int
    # 出牌顺序：row-major | col-major
    scan_order: str = "row-major"
    # horizontal: 第一行靠近桌心还是靠近玩家
    grow_direction: str = "away"

    def slot_positions(self) -> list[tuple[int, int, Rect]]:
        """
        返回按出牌顺序排列的 (row, col, rect) 列表。
        最多 rows * cols 个槽位。
        """
        positions: list[tuple[int, int, Rect]] = []
        for row in range(self.rows):
            for col in range(self.cols):
                if self.orientation == RiverOrientation.HORIZONTAL:
                    x = self.rect.x + col * self.tile_width
                    y = self.rect.y + row * self.tile_height
                else:
                    x = self.rect.x + col * self.tile_width
                    y = self.rect.y + row * self.tile_height
                positions.append((
                    row, col,
                    Rect(x, y, self.tile_width, self.tile_height),
                ))

        # 按 Majsoul 出牌顺序排序
        if self.orientation == RiverOrientation.HORIZONTAL:
            if self.grow_direction == "away":
                # 先近后远：self 从靠近玩家的行开始
                positions.sort(key=lambda p: (p[0], p[1]))
            else:
                positions.sort(key=lambda p: (-p[0], p[1]))
        else:
            # 纵向牌河：按 col then row
            if self.scan_order == "col-major":
                positions.sort(key=lambda p: (p[1], p[0]))
            else:
                positions.sort(key=lambda p: (p[0], p[1]))

        return positions

    @classmethod
    def from_dict(cls, screen_pos: str, data: dict[str, Any]) -> "RiverLayout":
        r = data["rect"]
        return cls(
            screen_pos=screen_pos,
            rect=Rect(r["x"], r["y"], r["width"], r["height"]),
            orientation=RiverOrientation(data.get("orientation", "horizontal")),
            rows=data.get("rows", 3),
            cols=data.get("cols", 6),
            tile_width=data.get("tile_width", 42),
            tile_height=data.get("tile_height", 50),
            scan_order=data.get("scan_order", "row-major"),
            grow_direction=data.get("grow_direction", "away"),
        )


@dataclass
class MeldLayout:
    """副露区域布局。"""
    screen_pos: str
    rect: Rect
    max_melds: int = 4
    tile_width: int = 36
    tile_height: int = 48

    @classmethod
    def from_dict(cls, screen_pos: str, data: dict[str, Any]) -> "MeldLayout":
        r = data["rect"]
        return cls(
            screen_pos=screen_pos,
            rect=Rect(r["x"], r["y"], r["width"], r["height"]),
            max_melds=data.get("max_melds", 4),
            tile_width=data.get("tile_width", 36),
            tile_height=data.get("tile_height", 48),
        )


@dataclass
class RegionConfig:
    hand: Rect
    dora: Rect
    max_hand_slots: int
    river_layouts: dict[str, RiverLayout]
    meld_layouts: dict[str, MeldLayout]
    dora_slots: Rect | None = None

    @classmethod
    def from_config(cls, vision_cfg: dict[str, Any]) -> "RegionConfig":
        h = vision_cfg["hand"]
        d = vision_cfg["dora"]

        river_layouts = {}
        for pos, data in vision_cfg.get("rivers", {}).items():
            if "rect" in data:
                river_layouts[pos] = RiverLayout.from_dict(pos, data)

        meld_layouts = {}
        for pos, data in vision_cfg.get("melds", {}).items():
            if "rect" in data:
                meld_layouts[pos] = MeldLayout.from_dict(pos, data)

        dora_slots = None
        if "dora_slots" in vision_cfg:
            ds = vision_cfg["dora_slots"]
            dora_slots = Rect(ds["x"], ds["y"], ds["width"], ds["height"])

        return cls(
            hand=Rect(h["x"], h["y"], h["width"], h["height"]),
            dora=Rect(d["x"], d["y"], d["width"], d["height"]),
            max_hand_slots=h.get("max_slots", 14),
            river_layouts=river_layouts,
            meld_layouts=meld_layouts,
            dora_slots=dora_slots,
        )

    def screen_to_mjai_player(self, screen_pos: str, self_seat: int) -> int:
        """屏幕方位 -> MJAI player id。"""
        offset = {"self": 0, "right": 1, "across": 2, "left": 3}
        return (self_seat + offset.get(screen_pos, 0)) % 4


def detect_tile_in_slot(
    slot_bgr: np.ndarray,
    brightness_threshold: int = 40,
    min_size: tuple[int, int] = (8, 8),
) -> bool:
    """检测槽位内是否有牌（基于亮度）。"""
    if slot_bgr.size == 0:
        return False
    h, w = slot_bgr.shape[:2]
    if h < min_size[1] or w < min_size[0]:
        return False
    gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    cx1, cx2 = int(w * 0.2), int(w * 0.8)
    cy1, cy2 = int(h * 0.15), int(h * 0.85)
    region = gray[cy1:cy2, cx1:cx2]
    return float(np.mean(region)) > brightness_threshold
