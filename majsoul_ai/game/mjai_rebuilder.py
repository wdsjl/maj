"""从视觉快照完整重建 MJAI 事件流。"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from majsoul_ai.game.snapshot import GameSnapshot, MeldGroup
from majsoul_ai.game.tiles import sort_tiles

logger = logging.getLogger(__name__)


class MjaiRebuilder:
    """
    根据完整视觉快照重建 MJAI 事件序列。

    重建策略：
    1. start_game / start_kyoku 从快照元数据生成
    2. 按回合顺序交织四家牌河，插入 tsumo + dahai
    3. 在对应时机插入副露事件（chi/pon/kan）
    4. 轮到自己且手牌 14 张时，在末尾追加 tsumo 等待 AI 决策
    """

    def __init__(self, player_id: int = 0) -> None:
        self.player_id = player_id
        self._last_events_hash: str = ""
        self._cached_events: list[dict[str, Any]] = []

    def rebuild(self, snap: GameSnapshot) -> list[dict[str, Any]]:
        """从快照完整重建事件流。"""
        if not snap.in_kyoku and len(snap.hand) < 13:
            return []

        events: list[dict[str, Any]] = [
            {"type": "start_game", "names": ["0", "1", "2", "3"], "id": self.player_id},
        ]

        tehais = self._build_tehais(snap)
        kyoku_event: dict[str, Any] = {
            "type": "start_kyoku",
            "bakaze": snap.bakaze,
            "kyoku": snap.kyoku,
            "honba": snap.honba,
            "kyotaku": snap.kyotaku,
            "oya": snap.oya,
            "scores": snap.scores,
            "tehais": tehais,
        }
        if snap.dora:
            kyoku_event["dora_marker"] = snap.dora
        events.append(kyoku_event)

        # 按全局回合顺序重建打牌与副露
        events.extend(self._rebuild_turns(snap))

        # 若轮到自己且已摸牌，确保末尾有 tsumo 事件
        if snap.is_my_turn and len(snap.hand) == 14:
            events = self._ensure_pending_tsumo(events, snap)

        self._cached_events = events
        return deepcopy(events)

    def _build_tehais(self, snap: GameSnapshot) -> list[list[str]]:
        """构建 start_kyoku 的 tehais。"""
        tehais: list[list[str]] = [["?"] * 13 for _ in range(4)]

        # 自家手牌：若当前 14 张则去掉最后一张（视为刚摸的）
        hand = sort_tiles(snap.hand)
        if len(hand) == 14:
            initial = hand[:-1]
        else:
            initial = hand[:13]
        tehais[self.player_id] = initial if len(initial) == 13 else (initial + ["?"] * 13)[:13]

        return tehais

    def _rebuild_turns(self, snap: GameSnapshot) -> list[dict[str, Any]]:
        """按全局回合顺序重建 tsumo/dahai，并插入副露事件。"""
        events: list[dict[str, Any]] = []
        oya = snap.oya
        rivers = {p: list(snap.rivers.get(p, [])) for p in range(4)}
        melds = {p: list(snap.melds.get(p, [])) for p in range(4)}

        total = sum(len(rivers[p]) for p in range(4))
        discard_idx = {p: 0 for p in range(4)}
        meld_inserted = {p: False for p in range(4)}

        emitted = 0
        turn = 0
        max_turns = total * 4 + 4  # 安全上限

        while emitted < total and turn < max_turns:
            actor = (oya + turn) % 4
            turn += 1

            if discard_idx[actor] >= len(rivers[actor]):
                continue  # 该玩家已无牌可出，跳过此回合 slot

            # 在该玩家第一次出牌前插入副露
            if not meld_inserted[actor] and melds[actor]:
                for meld in melds[actor]:
                    events.extend(self._meld_to_events(meld, actor, snap, events))
                meld_inserted[actor] = True

            pai = rivers[actor][discard_idx[actor]]
            discard_idx[actor] += 1
            emitted += 1

            tsumo_pai = self._tsumo_pai(actor, snap, events)
            events.append({"type": "tsumo", "actor": actor, "pai": tsumo_pai})
            tsumogiri = self._infer_tsumogiri(actor, pai, tsumo_pai)
            events.append({
                "type": "dahai", "actor": actor, "pai": pai, "tsumogiri": tsumogiri,
            })

        return events

    def _meld_to_events(
        self,
        meld: MeldGroup,
        actor: int,
        snap: GameSnapshot,
        prior_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """将副露转为 MJAI 事件。"""
        events: list[dict[str, Any]] = []
        tiles = meld.tiles

        if meld.meld_type == "chi" and len(tiles) >= 3:
            target = self._find_meld_target(prior_events, actor)
            called = tiles[0]
            consumed = tiles[1:3]
            events.append({
                "type": "chi", "actor": actor, "target": target,
                "pai": called, "consumed": consumed,
            })
        elif meld.meld_type in ("pon", "daiminkan") and len(tiles) >= 3:
            target = self._find_meld_target(prior_events, actor)
            called = tiles[0]
            consumed = [t for t in tiles[1:3] if t != called][:2]
            if meld.meld_type == "daiminkan":
                events.append({
                    "type": "daiminkan", "actor": actor, "target": target,
                    "pai": called, "consumed": tiles[1:4] if len(tiles) >= 4 else consumed,
                })
            else:
                events.append({
                    "type": "pon", "actor": actor, "target": target,
                    "pai": called, "consumed": consumed if len(consumed) == 2 else tiles[1:3],
                })
        elif meld.meld_type == "ankan" and len(tiles) >= 4:
            events.append({"type": "ankan", "actor": actor, "consumed": tiles[:4]})
        elif meld.meld_type == "kakan" and len(tiles) >= 4:
            events.append({
                "type": "kakan", "actor": actor,
                "pai": tiles[0], "consumed": tiles[1:3],
            })

        return events

    def _find_meld_target(self, events: list[dict[str, Any]], actor: int) -> int:
        """找到最近一位打牌的玩家（副露来源）。"""
        for ev in reversed(events):
            if ev.get("type") == "dahai" and ev.get("actor") != actor:
                return ev["actor"]
        return (actor + 3) % 4

    def _tsumo_pai(
        self,
        actor: int,
        snap: GameSnapshot,
        prior_events: list[dict[str, Any]] | None = None,
    ) -> str:
        """推断摸到的牌。"""
        if actor != self.player_id:
            return "?"

        hand = sort_tiles(snap.hand)
        if len(hand) < 14:
            return "?"

        # 从当前手牌推断刚摸的牌
        if prior_events:
            hand_after = self._hand_from_events(prior_events, self.player_id)
            drawn = self._find_drawn(hand_after, hand)
            if drawn:
                return drawn

        return hand[-1]

    def _hand_from_events(self, events: list[dict[str, Any]], player: int) -> list[str]:
        """从事件流推算玩家当前手牌。"""
        hand: list[str] = []
        for ev in events:
            t = ev.get("type")
            if t == "start_kyoku":
                tehais = ev.get("tehais", [])
                if player < len(tehais):
                    hand = [x for x in tehais[player] if x != "?"]
            elif t == "tsumo" and ev.get("actor") == player:
                hand.append(ev["pai"])
            elif t == "dahai" and ev.get("actor") == player:
                pai = ev["pai"]
                if pai in hand:
                    hand.remove(pai)
            elif ev.get("actor") == player and t in ("chi", "pon", "daiminkan", "ankan", "kakan"):
                consumed = ev.get("consumed", [])
                for c in consumed:
                    if c in hand:
                        hand.remove(c)
                if t in ("chi", "pon", "daiminkan"):
                    pai = ev.get("pai")
                    if pai and pai in hand:
                        hand.remove(pai)
        return sort_tiles(hand)

    def _find_drawn(self, old: list[str], new: list[str]) -> str | None:
        if len(new) != len(old) + 1:
            return new[-1] if new else None
        old_copy = old.copy()
        for t in new:
            if t in old_copy:
                old_copy.remove(t)
            else:
                return t
        return new[-1]

    def _infer_tsumogiri(self, actor: int, dahai: str, tsumo: str) -> bool:
        return actor == self.player_id and dahai == tsumo and tsumo != "?"

    def _ensure_pending_tsumo(
        self, events: list[dict[str, Any]], snap: GameSnapshot
    ) -> list[dict[str, Any]]:
        """确保末尾有自家待决策的 tsumo。"""
        if not events:
            return events

        last = events[-1]
        hand = sort_tiles(snap.hand)
        drawn = hand[-1] if hand else "?"

        if last.get("type") == "tsumo" and last.get("actor") == self.player_id:
            # 已有 tsumo，更新 pai
            if drawn != "?":
                last["pai"] = drawn
            return events

        if last.get("type") == "dahai":
            # 上家刚打牌，轮到自己摸牌
            events.append({"type": "tsumo", "actor": self.player_id, "pai": drawn})
            return events

        return events

    def needs_ai_decision(self, snap: GameSnapshot) -> bool:
        """是否需要向 AI 请求决策。"""
        if not snap.is_my_turn or len(snap.hand) != 14:
            return False
        events = self.rebuild(snap)
        if not events:
            return False
        last = events[-1]
        return last.get("type") == "tsumo" and last.get("actor") == self.player_id

    def get_cached_events(self) -> list[dict[str, Any]]:
        return deepcopy(self._cached_events)


class MjaiStateTracker:
    """
    状态追踪器：整合快照识别与 MJAI 重建，处理 AI 决策应用。
    """

    def __init__(self, player_id: int = 0) -> None:
        self.player_id = player_id
        self.rebuilder = MjaiRebuilder(player_id)
        self._last_hand: list[str] = []
        self._in_kyoku = False
        self._last_recommendation_applied = False

    def reset(self) -> None:
        self._last_hand.clear()
        self._in_kyoku = False
        self._last_recommendation_applied = False
        self.rebuilder = MjaiRebuilder(self.player_id)

    def update(self, snap: GameSnapshot) -> tuple[list[dict[str, Any]], bool]:
        """
        更新状态。
        返回 (events, needs_ai_decision)
        """
        # 检测新局：牌河清空 + 13 张手牌
        if self._detect_new_kyoku(snap):
            self.reset()
            self._in_kyoku = True

        if len(snap.hand) >= 13:
            snap.in_kyoku = True
            self._in_kyoku = True

        if not snap.in_kyoku:
            return [], False

        events = self.rebuilder.rebuild(snap)
        needs_ai = self.rebuilder.needs_ai_decision(snap)
        self._last_hand = sort_tiles(snap.hand)
        return events, needs_ai

    def _detect_new_kyoku(self, snap: GameSnapshot) -> bool:
        """检测是否开始新一局。"""
        total_river = snap.total_discards
        if total_river == 0 and len(snap.hand) == 13 and self._in_kyoku:
            # 牌河空 + 13张手牌 -> 新局
            return True
        if not self._in_kyoku and len(snap.hand) >= 13 and total_river == 0:
            return True
        return False

    def apply_ai_reaction(self, reaction: dict[str, Any], snap: GameSnapshot) -> None:
        """记录 AI 决策（下一帧 rebuild 时会从视觉状态重新推导）。"""
        self._last_recommendation_applied = True
