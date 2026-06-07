"""副露（吃/碰/杠）识别。"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

import cv2
import numpy as np

from majsoul_ai.game.snapshot import MeldGroup
from majsoul_ai.vision.regions import detect_tile_in_slot

if TYPE_CHECKING:
    from majsoul_ai.vision.regions import MeldLayout, RegionConfig
    from majsoul_ai.vision.tiles import TileRecognizer

logger = logging.getLogger(__name__)

# 每组副露占用的横向宽度（像素）
MELD_GROUP_WIDTH = 110


class MeldScanner:
    """扫描四家副露区域。"""

    def __init__(
        self,
        regions: "RegionConfig",
        recognizer: "TileRecognizer",
        self_seat: int = 0,
    ) -> None:
        self.regions = regions
        self.recognizer = recognizer
        self.self_seat = self_seat

    def scan_all(self, frame_bgr: np.ndarray) -> dict[int, list[MeldGroup]]:
        result: dict[int, list[MeldGroup]] = {i: [] for i in range(4)}

        for screen_pos, layout in self.regions.meld_layouts.items():
            player_id = self.regions.screen_to_mjai_player(screen_pos, self.self_seat)
            result[player_id] = self._scan_melds(frame_bgr, layout)

        return result

    def _scan_melds(self, frame_bgr: np.ndarray, layout: "MeldLayout") -> list[MeldGroup]:
        melds: list[MeldGroup] = []
        area = layout.rect.crop(frame_bgr)
        if area.size == 0:
            return melds

        # 按组扫描：每组约 3-4 张牌宽
        group_w = MELD_GROUP_WIDTH
        x_offset = 0
        for _ in range(layout.max_melds):
            if x_offset + group_w > layout.rect.width:
                break

            group_rect_x = layout.rect.x + x_offset
            group_crop = frame_bgr[
                layout.rect.y: layout.rect.y + layout.rect.height,
                group_rect_x: group_rect_x + group_w,
            ]
            if not self._has_meld_content(group_crop):
                break

            tiles = self._recognize_meld_tiles(group_crop, layout)
            if len(tiles) < 3:
                break

            meld_type = self._infer_meld_type(tiles)
            conf = sum(t[1] for t in tiles) / len(tiles)
            tile_names = [t[0] for t in tiles if t[0]]

            if len(tile_names) >= 3:
                melds.append(MeldGroup(
                    meld_type=meld_type,
                    tiles=tile_names,
                    confidence=conf,
                ))

            x_offset += group_w

        return melds

    def _has_meld_content(self, crop: np.ndarray) -> bool:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray)) > 45

    def _recognize_meld_tiles(
        self, group_crop: np.ndarray, layout: "MeldLayout"
    ) -> list[tuple[str | None, float]]:
        """识别一组副露中的牌（最多 4 张）。"""
        h, w = group_crop.shape[:2]
        tile_w = layout.tile_width
        results: list[tuple[str | None, float]] = []

        for i in range(4):
            x1 = i * tile_w
            if x1 + tile_w > w:
                break
            tile_crop = group_crop[:, x1: x1 + tile_w]
            if not detect_tile_in_slot(tile_crop, brightness_threshold=35):
                if i >= 3:
                    break
                continue
            tile, conf = self.recognizer.recognize(tile_crop)
            if tile:
                results.append((tile, conf))

        return results

    def _infer_meld_type(self, tiles: list[tuple[str | None, float]]) -> str:
        """根据牌型推断副露类型。"""
        names = [t[0] for t in tiles if t[0]]
        if not names:
            return "pon"

        counts = Counter(names)
        if len(names) == 4:
            if len(counts) == 1:
                return "daiminkan" if True else "ankan"
            return "kakan"
        if len(names) == 3:
            if len(counts) == 1:
                return "pon"
            # 尝试判断顺子 (chi)
            if self._is_sequence(names):
                return "chi"
            return "pon"
        return "pon"

    def _is_sequence(self, tiles: list[str]) -> bool:
        """判断三张数牌是否构成顺子。"""
        if len(tiles) != 3:
            return False
        suits = {t[-1] for t in tiles if len(t) >= 2 and t[-1] in "mps"}
        if len(suits) != 1:
            return False
        try:
            nums = sorted(int(t[0]) for t in tiles)
            return nums[1] == nums[0] + 1 and nums[2] == nums[1] + 1
        except ValueError:
            return False

    def draw_debug(
        self, frame_bgr: np.ndarray, melds: dict[int, list[MeldGroup]] | None = None
    ) -> np.ndarray:
        out = frame_bgr.copy()
        colors = {0: (0, 255, 0), 1: (255, 128, 0), 2: (0, 128, 255), 3: (255, 0, 255)}

        for screen_pos, layout in self.regions.meld_layouts.items():
            pid = self.regions.screen_to_mjai_player(screen_pos, self.self_seat)
            color = colors.get(pid, (200, 200, 200))
            cv2.rectangle(
                out,
                (layout.rect.x, layout.rect.y),
                (layout.rect.x + layout.rect.width, layout.rect.y + layout.rect.height),
                color, 2,
            )
            if melds and pid in melds:
                label = f"P{pid}:{len(melds[pid])}组"
                cv2.putText(
                    out, label,
                    (layout.rect.x, layout.rect.y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1,
                )
        return out
