"""MJAI 状态构建（兼容旧接口，委托给 MjaiStateTracker）。"""

from __future__ import annotations

from majsoul_ai.game.mjai_rebuilder import MjaiStateTracker
from majsoul_ai.game.snapshot import GameSnapshot

# 向后兼容
MjaiStateBuilder = MjaiStateTracker

__all__ = ["GameSnapshot", "MjaiStateBuilder", "MjaiStateTracker"]
