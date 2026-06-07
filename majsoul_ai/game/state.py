"""MJAI 事件构建与游戏状态追踪。"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from majsoul_ai.game.tiles import sort_tiles

logger = logging.getLogger(__name__)


@dataclass
class GameSnapshot:
    """当前视觉识别到的游戏快照。"""
    hand: list[str] = field(default_factory=list)
    hand_confidence: float = 0.0
    dora: str | None = None
    is_my_turn: bool = False
    tile_count: int = 0


class MjaiStateBuilder:
    """
    从视觉识别结果增量构建 MJAI 事件流。
    屏幕识别模式下无法获取完整牌局信息，采用启发式重建。
    """

    def __init__(self, player_id: int = 0) -> None:
        self.player_id = player_id
        self.events: list[dict[str, Any]] = []
        self._last_hand: list[str] = []
        self._in_kyoku = False
        self._current_actor = 0
        self._pending_tsumo: str | None = None

    def reset(self) -> None:
        self.events.clear()
        self._last_hand.clear()
        self._in_kyoku = False
        self._current_actor = 0
        self._pending_tsumo = None

    def start_game(self) -> None:
        self.events = [{"type": "start_game", "names": ["0", "1", "2", "3"], "id": self.player_id}]
        self._in_kyoku = False

    def start_kyoku(self, hand: list[str], dora: str | None = None) -> None:
        """开始新一局（视觉模式下手动或自动触发）。"""
        tehais: list[list[str]] = [["?" ] * 13 for _ in range(4)]
        tehais[self.player_id] = sort_tiles(hand[:13])

        event: dict[str, Any] = {
            "type": "start_kyoku",
            "bakaze": "E",
            "kyoku": 1,
            "honba": 0,
            "kyotaku": 0,
            "oya": 0,
            "scores": [25000, 25000, 25000, 25000],
            "tehais": tehais,
        }
        if dora:
            event["dora_marker"] = dora
        self.events.append(event)
        self._in_kyoku = True
        self._last_hand = sort_tiles(hand[:13])
        self._current_actor = 0
        self._pending_tsumo = None

    def update_from_snapshot(self, snap: GameSnapshot) -> bool:
        """
        根据最新快照更新 MJAI 事件。
        返回 True 表示需要向 AI 请求决策。
        """
        if not snap.hand:
            return False

        hand = sort_tiles(snap.hand)

        if not self._in_kyoku:
            self.start_game()
            self.start_kyoku(hand, snap.dora)
            if len(hand) == 14:
                drawn = self._find_drawn_tile(self._last_hand, hand)
                if drawn:
                    self._append_tsumo(self.player_id, drawn)
                    self._pending_tsumo = drawn
                return True
            return False

        if len(hand) == 14 and snap.is_my_turn:
            if hand != self._last_hand:
                drawn = self._find_drawn_tile(self._last_hand, hand)
                if drawn and drawn != self._pending_tsumo:
                    self._append_tsumo(self.player_id, drawn)
                    self._pending_tsumo = drawn
                    self._last_hand = hand
                    return True
                elif self._pending_tsumo and self._count_tile(hand, self._pending_tsumo) > 0:
                    self._last_hand = hand
                    return True

        elif len(hand) == 13 and self._last_hand and len(self._last_hand) == 14:
            discarded = self._find_discarded(self._last_hand, hand)
            if discarded:
                self._append_dahai(self.player_id, discarded, tsumogiri=False)
            self._last_hand = hand
            self._pending_tsumo = None

        return False

    def _find_drawn_tile(self, old: list[str], new: list[str]) -> str | None:
        if len(new) != len(old) + 1:
            return new[-1] if new else None
        old_copy = old.copy()
        for t in new:
            if t in old_copy:
                old_copy.remove(t)
            else:
                return t
        return new[-1] if new else None

    def _find_discarded(self, old: list[str], new: list[str]) -> str | None:
        if len(old) != len(new) + 1:
            return None
        new_copy = new.copy()
        for t in old:
            if t in new_copy:
                new_copy.remove(t)
            else:
                return t
        return None

    def _count_tile(self, tiles: list[str], tile: str) -> int:
        return tiles.count(tile)

    def _append_tsumo(self, actor: int, pai: str) -> None:
        self.events.append({"type": "tsumo", "actor": actor, "pai": pai})
        self._current_actor = actor

    def _append_dahai(self, actor: int, pai: str, tsumogiri: bool) -> None:
        self.events.append({
            "type": "dahai",
            "actor": actor,
            "pai": pai,
            "tsumogiri": tsumogiri,
        })

    def get_events_for_ai(self) -> list[dict[str, Any]]:
        return deepcopy(self.events)

    def apply_ai_reaction(self, reaction: dict[str, Any]) -> None:
        """将 AI 决策应用到事件流。"""
        rtype = reaction.get("type")
        if rtype == "dahai":
            pai = reaction["pai"]
            tsumogiri = reaction.get("tsumogiri", False)
            self._append_dahai(reaction.get("actor", self.player_id), pai, tsumogiri)
            if self._last_hand and pai in self._last_hand:
                h = self._last_hand.copy()
                h.remove(pai)
                self._last_hand = sort_tiles(h)
            self._pending_tsumo = None
        elif rtype == "reach":
            self.events.append({"type": "reach", "actor": reaction.get("actor", self.player_id)})
