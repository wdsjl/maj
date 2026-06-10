"""游戏视觉快照数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiverTile:
    """牌河中的单张牌。"""
    tile: str | None
    confidence: float
    row: int
    col: int


@dataclass
class MeldGroup:
    """副露（吃碰杠）。"""
    meld_type: str  # chi | pon | daiminkan | ankan | kakan
    tiles: list[str]
    confidence: float = 0.0
    from_player: int | None = None  # 鸣牌来源（MJAI player id）


@dataclass
class GameSnapshot:
    """当前视觉识别到的完整游戏快照。"""
    hand: list[str] = field(default_factory=list)
    hand_confidence: float = 0.0
    dora: str | None = None
    dora_indicators: list[str] = field(default_factory=list)
    is_my_turn: bool = False
    tile_count: int = 0
    # MJAI player id -> 按出牌顺序排列的牌河
    rivers: dict[int, list[str]] = field(default_factory=dict)
    river_confidence: float = 0.0
    # MJAI player id -> 副露列表
    melds: dict[int, list[MeldGroup]] = field(default_factory=dict)
    # 场风/局数（视觉 OCR 暂不可用时为默认值）
    bakaze: str = "E"
    kyoku: int = 1
    honba: int = 0
    kyotaku: int = 0
    oya: int = 0
    scores: list[int] = field(default_factory=lambda: [25000, 25000, 25000, 25000])
    in_kyoku: bool = False

    @property
    def total_discards(self) -> int:
        return sum(len(r) for r in self.rivers.values())

    def river_summary(self) -> str:
        parts = []
        for pid in sorted(self.rivers.keys()):
            tiles = self.rivers[pid]
            if tiles:
                parts.append(f"P{pid}:{len(tiles)}")
        return " ".join(parts) if parts else "无"
