"""调试窗口捕捉、手牌与牌河识别。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    import cv2
    from majsoul_ai.config import load_config
    from majsoul_ai.capture.window import WindowCapture
    from majsoul_ai.vision.align import ScreenAligner
    from majsoul_ai.vision.regions import RegionConfig
    from majsoul_ai.vision.tiles import TileRecognizer
    from majsoul_ai.vision.river import RiverScanner
    from majsoul_ai.vision.melds import MeldScanner
    from majsoul_ai.game.mjai_rebuilder import MjaiRebuilder
    from majsoul_ai.game.snapshot import GameSnapshot

    cfg = load_config()
    self_seat = cfg["game"]["seat"]
    regions = RegionConfig.from_config(cfg["vision"])
    recognizer = TileRecognizer(cfg["paths"]["templates_dir"])
    aligner = ScreenAligner(
        cfg["vision"]["standard_width"],
        cfg["vision"]["standard_height"],
    )

    if sys.platform == "win32":
        capture = WindowCapture(cfg["window"]["title_keywords"])
        info = capture.find_window()
        if not info:
            print("未找到雀魂窗口")
            sys.exit(1)
        frame = capture.capture()
    else:
        print("非 Windows: 使用合成测试图像")
        import numpy as np
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, "Demo", (500, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

    aligned = aligner.transform(frame)
    river_scanner = RiverScanner(regions, recognizer, self_seat)
    meld_scanner = MeldScanner(regions, recognizer, self_seat)

    # 手牌区域
    h = regions.hand
    cv2.rectangle(aligned, (h.x, h.y), (h.x + h.width, h.y + h.height), (0, 255, 0), 2)
    hand_results = recognizer.recognize_hand(aligned, regions.hand, regions.max_hand_slots)
    hand_tiles = [t for t, _c, _i in hand_results if t]

    # 牌河 + 副露标注
    rivers = river_scanner.scan_all(aligned)
    melds = meld_scanner.scan_all(aligned)
    aligned = river_scanner.draw_debug(aligned, rivers)
    aligned = meld_scanner.draw_debug(aligned, melds)

    # MJAI 重建测试
    snap = GameSnapshot(
        hand=hand_tiles,
        is_my_turn=len(hand_tiles) >= 14,
        in_kyoku=len(hand_tiles) >= 13 or sum(len(r) for r in rivers.values()) > 0,
        rivers=rivers,
        melds=melds,
        oya=cfg["game"].get("oya", 0),
    )
    events = MjaiRebuilder(self_seat).rebuild(snap)

    out = ROOT / "debug_capture.png"
    cv2.imwrite(str(out), aligned)
    print(f"已保存: {out}")
    print(f"手牌: {hand_tiles}")
    for pid, tiles in rivers.items():
        if tiles:
            print(f"  牌河 P{pid}: {tiles}")
    for pid, ms in melds.items():
        if ms:
            print(f"  副露 P{pid}: {[(m.meld_type, m.tiles) for m in ms]}")
    print(f"MJAI 事件数: {len(events)}")
    if events:
        print(f"  最后 3 条: {events[-3:]}")


if __name__ == "__main__":
    main()
