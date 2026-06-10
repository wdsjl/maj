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
from majsoul_ai.game.snapshot import GameSnapshot
from majsoul_ai.game.mjai_rebuilder import MjaiStateTracker
from majsoul_ai.game.tiles import AKA_DORA, ALL_TILES, tile_display

TEMPLATE_TOTAL = len(ALL_TILES) + len(AKA_DORA)
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
        from majsoul_ai.vision.river import RiverScanner
        from majsoul_ai.vision.melds import MeldScanner

        self_seat = self.cfg["game"]["seat"]
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
        self.river_scanner = RiverScanner(self.regions, self.recognizer, self_seat)
        self.meld_scanner = MeldScanner(self.regions, self.recognizer, self_seat)
        self.state_tracker = MjaiStateTracker(self_seat)

        mortal_cfg = self.cfg["mortal"]
        self.mortal = MortalClient(
            mortal_root=mortal_cfg.get("root", ""),
            player_id=mortal_cfg.get("player_id", self_seat),
            python_exe=mortal_cfg.get("python") or None,
            model_path=mortal_cfg.get("model_path") or None,
        )
        self.fallback = FallbackBot(mortal_cfg.get("player_id", self_seat))
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
        snap: GameSnapshot | None = None,
    ) -> None:
        if self._overlay:
            hand_str = " ".join(tile_display(t) for t in (hand or []))
            self._overlay.post_update(recommendation, status, hand_str)
            self._overlay.post_state(
                snap,
                self.recognizer.template_count,
                TEMPLATE_TOTAL,
            )

    def _analyze_frame(self, frame_bgr) -> GameSnapshot:
        """分析单帧，返回完整游戏快照。"""
        aligned = self.aligner.transform(frame_bgr)
        game_cfg = self.cfg["game"]

        # 手牌
        hand_results = self.recognizer.recognize_hand(
            aligned, self.regions.hand, self.regions.max_hand_slots
        )
        hand_tiles = [t for t, _c, _i in hand_results if t]
        confidences = [c for _t, c, _i in hand_results if c > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        tile_count = len(hand_results)
        is_my_turn = tile_count >= 14

        # 宝牌
        dora_tile = None
        dora_crop = self.regions.dora.crop(aligned)
        if dora_crop.size > 0:
            dora_tile, _ = self.recognizer.recognize(dora_crop)

        dora_indicators: list[str] = []
        if self.regions.dora_slots:
            slot_w = 48
            for i in range(5):
                x = self.regions.dora_slots.x + i * slot_w
                crop = aligned[
                    self.regions.dora_slots.y: self.regions.dora_slots.y + self.regions.dora_slots.height,
                    x: x + slot_w,
                ]
                if crop.size == 0:
                    break
                from majsoul_ai.vision.regions import detect_tile_in_slot
                if not detect_tile_in_slot(crop, brightness_threshold=50):
                    break
                t, _ = self.recognizer.recognize(crop)
                if t:
                    dora_indicators.append(t)

        # 牌河
        rivers = self.river_scanner.scan_all(aligned)
        river_confs = self.river_scanner.scan_detailed(aligned)
        river_conf_vals = [
            rt.confidence
            for tiles in river_confs.values()
            for rt in tiles
            if rt.confidence > 0
        ]
        river_avg = sum(river_conf_vals) / len(river_conf_vals) if river_conf_vals else 0.0

        # 副露
        melds = self.meld_scanner.scan_all(aligned)

        in_kyoku = len(hand_tiles) >= 13 or sum(len(r) for r in rivers.values()) > 0

        return GameSnapshot(
            hand=hand_tiles,
            hand_confidence=avg_conf,
            dora=dora_tile or (dora_indicators[0] if dora_indicators else None),
            dora_indicators=dora_indicators,
            is_my_turn=is_my_turn,
            tile_count=tile_count,
            rivers=rivers,
            river_confidence=river_avg,
            melds=melds,
            bakaze=game_cfg.get("bakaze", "E"),
            kyoku=game_cfg.get("kyoku", 1),
            honba=game_cfg.get("honba", 0),
            kyotaku=game_cfg.get("kyotaku", 0),
            oya=game_cfg.get("oya", 0),
            scores=game_cfg.get("scores", [25000, 25000, 25000, 25000]),
            in_kyoku=in_kyoku,
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
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        if self.recognizer.template_count < TEMPLATE_TOTAL:
            logger.warning(
                "牌面模板 %d/%d，建议运行: python -m tools.capture_templates",
                self.recognizer.template_count, TEMPLATE_TOTAL,
            )

        if not self._init_capture():
            if sys.platform != "win32":
                logger.info("非 Windows 环境，进入演示模式")
                self._demo_mode()
                return
            sys.exit(1)

        self._start_overlay()
        if self.mortal.is_available:
            self.mortal.start()

        self._running = True
        fps = self.cfg["window"].get("capture_fps", 5)
        interval = 1.0 / fps
        logger.info("开始实时分析 (FPS=%d, 含牌河识别)", fps)

        while self._running:
            t0 = time.time()

            frame = self._capture.capture()
            if frame is None:
                self._update_overlay("未找到雀魂窗口", None, [], None)
                time.sleep(1.0)
                continue

            snap = self._analyze_frame(frame)
            status = (
                f"手牌 {snap.tile_count} | 牌河 {snap.river_summary()} | "
                f"置信 {snap.hand_confidence:.0%}/{snap.river_confidence:.0%}"
            )

            if snap.hand or snap.total_discards > 0:
                events, need_ai = self.state_tracker.update(snap)

                if need_ai and snap.is_my_turn:
                    rec = self._query_ai(events)
                    if rec:
                        self._last_recommendation = rec
                        self.state_tracker.apply_ai_reaction(rec.raw, snap)
                        status = f"轮到你 | 牌河 {snap.river_summary()}"
                    self._update_overlay(status, self._last_recommendation, snap.hand, snap)
                else:
                    self._update_overlay(status, self._last_recommendation, snap.hand, snap)
            else:
                self._update_overlay("识别中...", None, [], snap)

            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))

        self.mortal.stop()

    def _demo_mode(self) -> None:
        """演示模式：含牌河重建的完整 MJAI 示例。"""
        from majsoul_ai.game.mjai_rebuilder import MjaiRebuilder

        self._start_overlay()
        snap = GameSnapshot(
            hand=["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "E", "S", "W", "N", "P"],
            is_my_turn=True,
            in_kyoku=True,
            dora="5s",
            rivers={
                0: ["9m", "8p"],
                1: ["3m", "7s"],
                2: ["F"],
                3: ["2s", "6m", "P"],
            },
            oya=0,
        )
        rebuilder = MjaiRebuilder(0)
        events = rebuilder.rebuild(snap)
        logger.info("演示 MJAI 事件数: %d", len(events))
        rec = self._query_ai(events)
        self._overlay.post_state(snap, 0, TEMPLATE_TOTAL)
        self._update_overlay(
            f"演示 | 牌河 {snap.river_summary()} | {len(events)} 事件",
            rec, snap.hand, snap,
        )
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
        assistant.state_tracker.player_id = args.player_id
        assistant.state_tracker.rebuilder.player_id = args.player_id

    try:
        assistant.run()
    except KeyboardInterrupt:
        assistant.stop()
        logger.info("已退出")


if __name__ == "__main__":
    main()
