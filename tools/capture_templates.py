"""
牌面模板采集工具。

用法:
  1. 启动雀魂并进入对局
  2. 运行: python -m tools.capture_templates
  3. 按提示将鼠标悬停在对应牌上，按 Enter 采集

采集的模板保存在 templates/tiles/ 目录。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from majsoul_ai.config import load_config
from majsoul_ai.game.tiles import ALL_TILES, AKA_DORA


def main() -> None:
    if sys.platform != "win32":
        print("模板采集需要在 Windows 上运行")
        sys.exit(1)

    import cv2
    from majsoul_ai.capture.window import WindowCapture
    from majsoul_ai.vision.align import ScreenAligner
    from majsoul_ai.vision.regions import RegionConfig, detect_tile_in_slot
    from majsoul_ai.vision.tiles import TileRecognizer

    cfg = load_config()
    capture = WindowCapture(cfg["window"]["title_keywords"])
    info = capture.find_window()
    if not info:
        print("未找到雀魂窗口")
        sys.exit(1)

    print(f"找到窗口: {info.title}")
    aligner = ScreenAligner(
        cfg["vision"]["standard_width"],
        cfg["vision"]["standard_height"],
        cfg["paths"].get("alignment_template"),
    )
    regions = RegionConfig.from_config(cfg["vision"])
    recognizer = TileRecognizer(cfg["paths"]["templates_dir"])

    all_tiles = ALL_TILES + AKA_DORA
    print(f"\n已有模板: {recognizer.template_count}/{len(all_tiles)}")
    print("操作说明:")
    print("  - 在雀魂中确保手牌可见")
    print("  - 输入牌名 (如 1m, 5p, E) 然后按 Enter 从当前手牌槽位采集")
    print("  - 输入 slot N 采集第 N 个槽位 (0-13)")
    print("  - 输入 list 列出缺失模板")
    print("  - 输入 q 退出\n")

    while True:
        cmd = input("> ").strip()
        if cmd.lower() in ("q", "quit", "exit"):
            break

        if cmd.lower() == "list":
            missing = [t for t in all_tiles if t not in recognizer._templates]
            print(f"缺失 {len(missing)} 个: {', '.join(missing[:20])}{'...' if len(missing) > 20 else ''}")
            continue

        frame = capture.capture()
        if frame is None:
            print("截图失败")
            continue

        aligned = aligner.transform(frame)
        slots = regions.hand.slot_rects(regions.max_hand_slots)

        if cmd.lower().startswith("slot "):
            try:
                idx = int(cmd.split()[1])
            except (IndexError, ValueError):
                print("用法: slot <0-13>")
                continue
            if idx < 0 or idx >= len(slots):
                print("槽位索引无效")
                continue
            tile_name = input(f"  槽位 {idx} 的牌名: ").strip()
            crop = slots[idx].crop(aligned)
            path = recognizer.save_template(crop, tile_name)
            print(f"  已保存: {path}")
            continue

        # 直接输入牌名：自动找最匹配的槽位
        tile_name = cmd
        if tile_name not in all_tiles:
            print(f"未知牌名: {tile_name}")
            continue

        # 显示当前手牌槽位
        print("  当前手牌槽位:")
        for i, slot in enumerate(slots):
            crop = slot.crop(aligned)
            if detect_tile_in_slot(crop):
                existing, conf = recognizer.recognize(crop)
                label = existing or "?"
                print(f"    [{i}] {label} ({conf:.0%})")

        idx_str = input(f"  选择槽位采集 '{tile_name}' (0-13): ").strip()
        try:
            idx = int(idx_str)
            crop = slots[idx].crop(aligned)
            path = recognizer.save_template(crop, tile_name)
            print(f"  已保存: {path}")
        except (ValueError, IndexError):
            print("无效槽位")


if __name__ == "__main__":
    main()
