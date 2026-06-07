"""Mortal AI 子进程客户端。"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from majsoul_ai.game.tiles import sort_tiles, tile_display

logger = logging.getLogger(__name__)


class MortalClient:
    """
    通过 stdin/stdout 与 Mortal (mortal.py) 通信。
    Mortal 协议：发送 JSON 数组（完整事件历史），接收单行 JSON 响应。
    """

    def __init__(
        self,
        mortal_root: str,
        player_id: int = 0,
        python_exe: str | None = None,
        model_path: str | None = None,
    ) -> None:
        self.mortal_root = Path(mortal_root) if mortal_root else None
        self.player_id = player_id
        self.python_exe = python_exe or sys.executable
        self.model_path = model_path
        self._proc: subprocess.Popen | None = None
        self._available = False

    @property
    def is_available(self) -> bool:
        if not self.mortal_root:
            return False
        mortal_py = self.mortal_root / "mortal" / "mortal.py"
        return mortal_py.exists()

    def start(self) -> bool:
        if not self.is_available:
            logger.warning("Mortal 未配置或 mortal.py 不存在")
            return False

        mortal_py = self.mortal_root / "mortal" / "mortal.py"
        cmd = [self.python_exe, str(mortal_py), str(self.player_id)]
        env = None
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.mortal_root / "mortal"),
                bufsize=1,
            )
            self._available = True
            logger.info("Mortal 进程已启动 (player_id=%d)", self.player_id)
            return True
        except Exception as e:
            logger.error("启动 Mortal 失败: %s", e)
            return False

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        self._available = False

    def query(self, events: list[dict[str, Any]]) -> dict[str, Any] | None:
        """发送事件历史，获取 AI 决策。"""
        if not self._proc or self._proc.poll() is not None:
            if not self.start():
                return None

        assert self._proc and self._proc.stdin and self._proc.stdout
        payload = json.dumps(events, separators=(",", ":"))
        try:
            self._proc.stdin.write(payload + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                logger.error("Mortal 无响应")
                return None
            return json.loads(line.strip())
        except Exception as e:
            logger.error("Mortal 通信错误: %s", e)
            self.stop()
            return None


class FallbackBot:
    """Mortal 不可用时的简易出牌 bot（基于向听数启发式）。"""

    def __init__(self, player_id: int = 0) -> None:
        self.player_id = player_id

    def query(self, events: list[dict[str, Any]]) -> dict[str, Any] | None:
        hand = self._extract_hand(events)
        if not hand or len(hand) < 14:
            return None

        # 简易策略：优先打孤张字牌，否则打最多的一张
        honors = {"E", "S", "W", "N", "P", "F", "C"}
        counts = Counter(hand)
        candidates = list(set(hand))

        def score_tile(t: str) -> float:
            s = 0.0
            if t in honors:
                s += 10.0
            s += counts[t] * 2.0
            if t.endswith("r"):
                s -= 20.0
            return s

        candidates.sort(key=score_tile, reverse=True)
        discard = candidates[0]
        tsumogiri = events[-1].get("type") == "tsumo" and events[-1].get("pai") == discard

        meta = [(t, 1.0 / (i + 1)) for i, t in enumerate(candidates[:5])]
        return {
            "type": "dahai",
            "actor": self.player_id,
            "pai": discard,
            "tsumogiri": tsumogiri,
            "meta_options": meta,
            "_fallback": True,
        }

    def _extract_hand(self, events: list[dict[str, Any]]) -> list[str]:
        hand: list[str] = []
        for ev in events:
            t = ev.get("type")
            if t == "start_kyoku":
                tehais = ev.get("tehais", [])
                if self.player_id < len(tehais):
                    hand = [x for x in tehais[self.player_id] if x != "?"]
            elif t == "tsumo" and ev.get("actor") == self.player_id:
                hand.append(ev["pai"])
            elif t == "dahai" and ev.get("actor") == self.player_id:
                pai = ev["pai"]
                if pai in hand:
                    hand.remove(pai)
        return sort_tiles(hand)


@dataclass
class AiRecommendation:
    action_type: str
    primary_tile: str | None
    action_text: str
    alternatives: list[tuple[str, float]]
    raw: dict[str, Any]


def reaction_to_recommendation(reaction: dict[str, Any]) -> AiRecommendation:
    """将 MJAI 响应转为 UI 展示结构。"""
    rtype = reaction.get("type", "none")
    pai = reaction.get("pai")
    alternatives: list[tuple[str, float]] = []

    if "meta_options" in reaction:
        for code, weight in reaction["meta_options"][:5]:
            alternatives.append((tile_display(code) if len(code) <= 3 else code, float(weight)))

    if rtype == "dahai" and pai:
        text = f"切 {tile_display(pai)}"
        if reaction.get("tsumogiri"):
            text += " (摸切)"
    elif rtype == "reach":
        text = "立直"
    elif rtype == "pon":
        text = f"碰 {tile_display(pai)}" if pai else "碰"
    elif rtype == "chi":
        text = f"吃 {tile_display(pai)}" if pai else "吃"
    elif rtype == "hora":
        text = "和牌!"
    elif rtype == "none":
        text = "跳过"
    else:
        text = rtype

    return AiRecommendation(
        action_type=rtype,
        primary_tile=pai,
        action_text=text,
        alternatives=alternatives,
        raw=reaction,
    )
