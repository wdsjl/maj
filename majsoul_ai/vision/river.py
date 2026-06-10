"""牌河（各家打出的牌）识别。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np

from majsoul_ai.game.snapshot import RiverTile
from majsoul_ai.vision.regions import detect_tile_in_slot

if TYPE_CHECKING:
    from majsoul_ai.vision.regions import RegionConfig, RiverLayout
    from majsoul_ai.vision.tiles import TileRecognizer

logger = logging.getLogger(__name__)


class RiverScanner:
    """扫描四家牌河，按出牌顺序返回牌列表。"""

    def __init__(
        self,
        regions: "RegionConfig",
        recognizer: "TileRecognizer",
        self_seat: int = 0,
        river_threshold: float | None = None,
    ) -> None:
        self.regions = regions
        self.recognizer = recognizer
        self.self_seat = self_seat
        self.river_threshold = river_threshold or recognizer.match_threshold * 0.9

    def scan_all(self, frame_bgr: np.ndarray) -> dict[int, list[str]]:
        """
        扫描所有玩家牌河。
        返回 { mjai_player_id: [tile, ...] }，按出牌先后顺序排列。
        """
        result: dict[int, list[str]] = {i: [] for i in range(4)}

        for screen_pos, layout in self.regions.river_layouts.items():
            player_id = self.regions.screen_to_mjai_player(screen_pos, self.self_seat)
            tiles = self._scan_river(frame_bgr, layout)
            result[player_id] = tiles

        return result

    def scan_detailed(self, frame_bgr: np.ndarray) -> dict[int, list[RiverTile]]:
        """带置信度的详细扫描。"""
        result: dict[int, list[RiverTile]] = {i: [] for i in range(4)}

        for screen_pos, layout in self.regions.river_layouts.items():
            player_id = self.regions.screen_to_mjai_player(screen_pos, self.self_seat)
            result[player_id] = self._scan_river_detailed(frame_bgr, layout)

        return result

    def _scan_river(self, frame_bgr: np.ndarray, layout: "RiverLayout") -> list[str]:
        tiles: list[str] = []
        for row, col, rect in layout.slot_positions():
            crop = rect.crop(frame_bgr)
            if not detect_tile_in_slot(crop, brightness_threshold=35):
                # 遇到空槽则停止——牌河按顺序填充，中间不会有空洞
                break
            tile, conf = self.recognizer.recognize(crop)
            if tile and conf >= self.river_threshold:
                tiles.append(tile)
            elif tile:
                tiles.append(tile)  # 低置信度仍保留，避免断链
            else:
                break
        return tiles

    def _scan_river_detailed(
        self, frame_bgr: np.ndarray, layout: "RiverLayout"
    ) -> list[RiverTile]:
        results: list[RiverTile] = []
        for row, col, rect in layout.slot_positions():
            crop = rect.crop(frame_bgr)
            if not detect_tile_in_slot(crop, brightness_threshold=35):
                break
            tile, conf = self.recognizer.recognize(crop)
            if tile is None:
                break
            results.append(RiverTile(tile=tile, confidence=conf, row=row, col=col))
        return results

    def draw_debug(
        self, frame_bgr: np.ndarray, rivers: dict[int, list[str]] | None = None
    ) -> np.ndarray:
        """在图像上标注牌河区域和识别结果。"""
        out = frame_bgr.copy()
        if rivers is None:
            rivers = self.scan_all(frame_bgr)

        colors = {0: (0, 255, 0), 1: (255, 128, 0), 2: (0, 128, 255), 3: (255, 0, 255)}

        for screen_pos, layout in self.regions.river_layouts.items():
            pid = self.regions.screen_to_mjai_player(screen_pos, self.self_seat)
            color = colors.get(pid, (200, 200, 200))

            cv2.rectangle(
                out,
                (layout.rect.x, layout.rect.y),
                (layout.rect.x + layout.rect.width, layout.rect.y + layout.rect.height),
                color, 1,
            )

            for idx, (row, col, rect) in enumerate(layout.slot_positions()):
                crop = rect.crop(frame_bgr)
                has_tile = detect_tile_in_slot(crop, brightness_threshold=35)
                c = color if has_tile else (80, 80, 80)
                cv2.rectangle(out, (rect.x, rect.y), (rect.x + rect.width, rect.y + rect.height), c, 1)

                if pid in rivers and idx < len(rivers[pid]):
                    label = rivers[pid][idx] or "?"
                    cv2.putText(
                        out, label, (rect.x + 2, rect.y + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1,
                    )

        return out
