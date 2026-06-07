"""牌面模板匹配识别。"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_ai.game.tiles import ALL_TILES, AKA_DORA

logger = logging.getLogger(__name__)

TILE_SIZE = (48, 64)  # 统一模板尺寸 (w, h)


class TileRecognizer:
    """基于 OpenCV 模板匹配的牌面识别器。"""

    def __init__(self, templates_dir: str, match_threshold: float = 0.75) -> None:
        self.templates_dir = Path(templates_dir)
        self.match_threshold = match_threshold
        self._templates: dict[str, np.ndarray] = {}
        self._load_templates()

    @property
    def template_count(self) -> int:
        return len(self._templates)

    def _load_templates(self) -> None:
        self._templates.clear()
        if not self.templates_dir.exists():
            logger.warning("模板目录不存在: %s", self.templates_dir)
            return

        for tile in ALL_TILES + AKA_DORA:
            for ext in (".png", ".jpg", ".jpeg"):
                path = self.templates_dir / f"{tile}{ext}"
                if path.exists():
                    img = cv2.imread(str(path))
                    if img is not None:
                        self._templates[tile] = self._normalize(img)
                    break

        logger.info("已加载 %d 个牌面模板", len(self._templates))

    def _normalize(self, img_bgr: np.ndarray) -> np.ndarray:
        return cv2.resize(img_bgr, TILE_SIZE, interpolation=cv2.INTER_AREA)

    def recognize(self, tile_bgr: np.ndarray) -> tuple[str | None, float]:
        """
        识别单张牌。
        返回 (牌名, 置信度)，无法识别时牌名为 None。
        """
        if not self._templates:
            return None, 0.0

        query = self._normalize(tile_bgr)
        best_tile: str | None = None
        best_score = 0.0

        for tile, tmpl in self._templates.items():
            result = cv2.matchTemplate(query, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(result.max())
            if score > best_score:
                best_score = score
                best_tile = tile

        if best_score >= self.match_threshold:
            return best_tile, best_score
        return None, best_score

    def recognize_hand(
        self, frame_bgr: np.ndarray, hand_rect, max_slots: int = 14
    ) -> list[tuple[str | None, float, int]]:
        """
        识别手牌区域所有槽位。
        返回 [(牌名, 置信度, 槽位索引), ...]
        """
        from majsoul_ai.vision.regions import detect_tile_in_slot

        slots = hand_rect.slot_rects(max_slots)
        results = []
        for i, slot in enumerate(slots):
            crop = slot.crop(frame_bgr)
            if crop.size == 0:
                continue
            if not detect_tile_in_slot(crop):
                continue
            tile, conf = self.recognize(crop)
            results.append((tile, conf, i))
        return results

    def save_template(self, tile_bgr: np.ndarray, tile_name: str) -> Path:
        """保存牌面模板。"""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        path = self.templates_dir / f"{tile_name}.png"
        cv2.imwrite(str(path), self._normalize(tile_bgr))
        self._templates[tile_name] = self._normalize(tile_bgr)
        return path
