"""调试窗口捕捉与识别。"""

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

    cfg = load_config()

    if sys.platform == "win32":
        capture = WindowCapture(cfg["window"]["title_keywords"])
        info = capture.find_window()
        if not info:
            print("未找到雀魂窗口")
            sys.exit(1)
        frame = capture.capture()
    else:
        print("非 Windows: 使用测试图像")
        frame = __import__("numpy").zeros((720, 1280, 3), dtype=__import__("numpy").uint8)
        cv2.putText(frame, "Demo Mode", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

    aligner = ScreenAligner(
        cfg["vision"]["standard_width"],
        cfg["vision"]["standard_height"],
    )
    aligned = aligner.transform(frame)
    regions = RegionConfig.from_config(cfg["vision"])
    recognizer = TileRecognizer(cfg["paths"]["templates_dir"])

    # 画出手牌区域
    h = regions.hand
    cv2.rectangle(aligned, (h.x, h.y), (h.x + h.width, h.y + h.height), (0, 255, 0), 2)

    results = recognizer.recognize_hand(aligned, regions.hand, regions.max_hand_slots)
    for tile, conf, idx in results:
        slots = regions.hand.slot_rects(regions.max_hand_slots)
        s = slots[idx]
        label = f"{tile or '?'} {conf:.0%}"
        cv2.putText(aligned, label, (s.x, s.y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    out = ROOT / "debug_capture.png"
    cv2.imwrite(str(out), aligned)
    print(f"已保存调试截图: {out}")
    print(f"识别到 {len(results)} 张牌")


if __name__ == "__main__":
    main()
