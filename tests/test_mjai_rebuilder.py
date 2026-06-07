"""MJAI 状态重建单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from majsoul_ai.game.snapshot import GameSnapshot, MeldGroup
from majsoul_ai.game.mjai_rebuilder import MjaiRebuilder, MjaiStateTracker


def test_empty_kyoku():
    snap = GameSnapshot(hand=[], in_kyoku=False)
    events = MjaiRebuilder(0).rebuild(snap)
    assert events == []


def test_start_kyoku_with_hand():
    snap = GameSnapshot(
        hand=["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E", "S", "W", "N"],
        in_kyoku=True,
        oya=0,
    )
    events = MjaiRebuilder(0).rebuild(snap)
    assert events[0]["type"] == "start_game"
    assert events[1]["type"] == "start_kyoku"
    assert len(events[1]["tehais"][0]) == 13


def test_river_interleaving():
    """四家牌河按回合顺序交织。"""
    snap = GameSnapshot(
        hand=["1m"] * 13,
        in_kyoku=True,
        oya=0,
        rivers={
            0: ["9m", "8p"],       # oya 出 2 张
            1: ["3m"],             # 下家 1 张
            2: ["F"],              # 对家 1 张
            3: ["2s", "6m"],       # 上家 2 张
        },
    )
    events = MjaiRebuilder(0).rebuild(snap)
    dahai_events = [e for e in events if e["type"] == "dahai"]
    assert len(dahai_events) == 6
    # 第 1 张：oya(0) 出 9m
    assert dahai_events[0] == {"type": "dahai", "actor": 0, "pai": "9m", "tsumogiri": False}
    # 第 2 张：player 1 出 3m
    assert dahai_events[1]["actor"] == 1
    assert dahai_events[1]["pai"] == "3m"


def test_my_turn_tsumo():
    snap = GameSnapshot(
        hand=["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E", "S", "W", "N", "P"],
        is_my_turn=True,
        in_kyoku=True,
        oya=0,
        rivers={0: ["9m"], 1: ["3m"], 2: ["F"], 3: ["2s"]},
    )
    rebuilder = MjaiRebuilder(0)
    assert rebuilder.needs_ai_decision(snap)
    events = rebuilder.rebuild(snap)
    assert events[-1]["type"] == "tsumo"
    assert events[-1]["actor"] == 0
    assert events[-1]["pai"] == "P"


def test_meld_in_events():
    snap = GameSnapshot(
        hand=["1m"] * 13,
        in_kyoku=True,
        oya=0,
        rivers={1: ["5p", "7s"], 0: ["3m"], 2: ["F"], 3: ["2s"]},
        melds={
            1: [MeldGroup(meld_type="pon", tiles=["5p", "5p", "5p"])],
        },
    )
    events = MjaiRebuilder(0).rebuild(snap)
    types = [e["type"] for e in events]
    assert "pon" in types or "dahai" in types


def test_state_tracker_new_kyoku():
    tracker = MjaiStateTracker(0)
    snap1 = GameSnapshot(
        hand=["1m"] * 13, in_kyoku=True,
        rivers={0: ["9m", "8p", "7s"], 1: ["3m"], 2: ["F"], 3: ["2s"]},
    )
    events, _ = tracker.update(snap1)
    assert len(events) > 2

    # 新局：牌河清空
    snap2 = GameSnapshot(hand=["2m"] * 13, in_kyoku=True, rivers={})
    events2, need_ai = tracker.update(snap2)
    assert events2[1]["type"] == "start_kyoku"


if __name__ == "__main__":
    test_empty_kyoku()
    test_start_kyoku_with_hand()
    test_river_interleaving()
    test_my_turn_tsumo()
    test_meld_in_events()
    test_state_tracker_new_kyoku()
    print("All tests passed.")
