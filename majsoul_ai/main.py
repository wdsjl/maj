"""主分析循环。"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

from majsoul_ai.ai.mortal import (
    AiRecommendation,
    FallbackBot,
    MortalClient,
    reaction_to_recommendation,
)
from majsoul_ai.config import load_config
from majsoul_ai.game.state import GameSnapshot, MjaiStateBuilder
from majsoul_ai.game.tiles import tile_display
from majsoul_ai.ui.overlay import OverlayController

logger = logging.getLogger(__name__)


class MajsoulAiAssistant:
    """雀魂 AI 实时分析主控制器。"""

    def __init__(self, config_path: str | None = None) -> None:
        self.cfg = load_config(config_path)
        self._running = False
        self._overlay_thread: threading.Thread | None = None
        self._overlay: OverlayController | None = None

        from majsoul_ai.vision.regions import RegionConfig
        from majsoul_ai.vision.tiles import TileRecognizer
        from majsoul_ai.vision.align import ScreenAligner

        self.regions = RegionConfig.from_config(self.cfg["vision"])
        self.recognizer = TileRecognizer(
            self.cfg["paths"]["templates_dir"],
            self.cfg["vision"]["match_threshold"],
        )
        self.aligner = ScreenAligner(
            self.cfg["vision"]["standard_width"],
            self.cfg["vision"]["standard_height"],
            self.cfg["paths"].get("alignment_template"),
        )
        self.state_builder = MjaiStateBuilder(self.cfg["game"]["seat"])

        mortal_cfg = self.cfg["mortal"]
        self.mortal = MortalClient(
            mortal_root=mortal_cfg.get("root", ""),
            player_id=mortal_cfg.get("player_id", 0),
            python_exe=mortal_cfg.get("python") or None,
            model_path=mortal_cfg.get("model_path") or None,
        )
        self.fallback = FallbackBot(mortal_cfg.get("player_id", 0))
        self.use_fallback = mortal_cfg.get("fallback_bot", True)

        self._last_recommendation: AiRecommendation | None = None
        self._capture = None

    def _init_capture(self) -> bool:
        if sys.platform != "win32":
            logger.error("此工具需要在 Windows 上运行以捕捉雀魂客户端窗口")
            return False

        from majsoul_ai.capture.window import WindowCapture

        self._capture = WindowCapture(self.cfg["window"]["title_keywords"])
        info = self._capture.find_window()
        if info is None:
            logger.error("未找到雀魂窗口，请确保游戏已启动")
            return False
        logger.info("已找到窗口: %s (%dx%d)", info.title, info.width, info.height)
        return True

    def _start_overlay(self) -> None:
        if not self.cfg["overlay"].get("enabled", True):
            return
        self._overlay = OverlayController(self.cfg["overlay"])
        self._overlay_thread = threading.Thread(
            target=self._overlay.run, name="OverlayThread", daemon=True
        )
        self._overlay_thread.start()
        time.sleep(0.5)

    def _update_overlay(
        self,
        status: str,
        recommendation: AiRecommendation | None = None,
        hand: list[str] | None = None,
    ) -> None:
        if self._overlay:
            hand_str = " ".join(tile_display(t) for t in (hand or []))
            self._overlay.post_update(recommendation, status, hand_str)

    def _analyze_frame(self, frame_bgr) -> GameSnapshot:
        """分析单帧，返回游戏快照。"""
        import cv2

        aligned = self.aligner.transform(frame_bgr)
        hand_results = self.recognizer.recognize_hand(
            aligned, self.regions.hand, self.regions.max_hand_slots
        )

        hand_tiles = [t for t, _c, _i in hand_results if t]
        confidences = [c for _t, c, _i in hand_results if c > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # 识别宝牌
        dora_crop = self.regions.dora.crop(aligned)
        dora_tile = None
        if dora_crop.size > 0:
            dora_tile, _ = self.recognizer.recognize(dora_crop)

        tile_count = len(hand_results)
        is_my_turn = tile_count >= 14

        return GameSnapshot(
            hand=hand_tiles,
            hand_confidence=avg_conf,
            dora=dora_tile,
            is_my_turn=is_my_turn,
            tile_count=tile_count,
        )

    def _query_ai(self, events: list[dict[str, Any]]) -> AiRecommendation | None:
        reaction = None
        if self.mortal.is_available:
            reaction = self.mortal.query(events)
        if reaction is None and self.use_fallback:
            reaction = self.fallback.query(events)
        if reaction:
            return reaction_to_recommendation(reaction)
        return None

    def run(self) -> None:
        """主循环。"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        if self.recognizer.template_count == 0:
            logger.warning(
                "未加载任何牌面模板！请先运行: python -m tools.capture_templates"
            )

        if not self._init_capture():
            if sys.platform != "win32":
                logger.info("非 Windows 环境，进入演示模式（无窗口捕捉）")
                self._demo_mode()
                return
            sys.exit(1)

        self._start_overlay()
        if self.mortal.is_available:
            self.mortal.start()

        self._running = True
        fps = self.cfg["window"].get("capture_fps", 5)
        interval = 1.0 / fps

        logger.info("开始实时分析 (FPS=%d)", fps)

        while self._running:
            t0 = time.time()

            frame = self._capture.capture()
            if frame is None:
                self._update_overlay("未找到雀魂窗口")
                time.sleep(1.0)
                continue

            snap = self._analyze_frame(frame)
            status = f"识别 {snap.tile_count} 张 | 置信度 {snap.hand_confidence:.0%}"

            if snap.hand:
                need_ai = self.state_builder.update_from_snapshot(snap)
                if need_ai and snap.is_my_turn:
                    events = self.state_builder.get_events_for_ai()
                    rec = self._query_ai(events)
                    if rec:
                        self._last_recommendation = rec
                        self.state_builder.apply_ai_reaction(rec.raw)
                        status = "轮到你出牌"
                    self._update_overlay(status, self._last_recommendation, snap.hand)
                else:
                    self._update_overlay(status, self._last_recommendation, snap.hand)
            else:
                self._update_overlay("识别中...", None, [])

            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))

        self.mortal.stop()

    def _demo_mode(self) -> None:
        """Linux/无窗口时的演示。"""
        self._start_overlay()
        events = [
            {"type": "start_game", "names": ["0", "1", "2", "3"], "id": 0},
            {
                "type": "start_kyoku",
                "bakaze": "E", "kyoku": 1, "honba": 0, "kyotaku": 0, "oya": 0,
                "scores": [25000, 25000, 25000, 25000],
                "dora_marker": "5s",
                "tehais": [
                    ["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E", "S", "W", "N"],
                    ["?"] * 13, ["?"] * 13, ["?"] * 13,
                ],
            },
            {"type": "tsumo", "actor": 0, "pai": "P"},
        ]
        rec = self._query_ai(events)
        demo_hand = ["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E", "S", "W", "N", "P"]
        self._update_overlay("演示模式", rec, demo_hand)
        if self._overlay and self._overlay.app:
            self._overlay.app.exec()

    def stop(self) -> None:
        self._running = False


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="雀魂麻将 AI 实时分析助手")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--mortal-root", help="Mortal 安装目录")
    parser.add_argument("--player-id", type=int, help="玩家座位 0-3")
    args = parser.parse_args()

    assistant = MajsoulAiAssistant(args.config)
    if args.mortal_root:
        assistant.mortal.mortal_root = __import__("pathlib").Path(args.mortal_root)
    if args.player_id is not None:
        assistant.mortal.player_id = args.player_id
        assistant.state_builder.player_id = args.player_id

    try:
        assistant.run()
    except KeyboardInterrupt:
        assistant.stop()
        logger.info("已退出")


if __name__ == "__main__":
    main()
