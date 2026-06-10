"""图形化牌面模板采集窗口。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from majsoul_ai.game.tiles import AKA_DORA, ALL_TILES, TILE_NAMES_ZH, TILE_UNICODE

if TYPE_CHECKING:
    from majsoul_ai.vision.tiles import TileRecognizer

ALL_TEMPLATE_TILES = ALL_TILES + AKA_DORA

TILE_GROUPS = [
    ("万子", [f"{n}m" for n in range(1, 10)]),
    ("筒子", [f"{n}p" for n in range(1, 10)]),
    ("索子", [f"{n}s" for n in range(1, 10)]),
    ("字牌", ["E", "S", "W", "N", "P", "F", "C"]),
    ("赤宝", AKA_DORA),
]


class TemplateCollectorWindow(QMainWindow):
    """牌面模板采集主窗口。"""

    def __init__(
        self,
        recognizer: "TileRecognizer",
        capture_fn,
        align_fn,
        hand_slots_fn,
        templates_dir: str,
    ) -> None:
        super().__init__()
        self.recognizer = recognizer
        self.capture_fn = capture_fn
        self.align_fn = align_fn
        self.hand_slots_fn = hand_slots_fn
        self.templates_dir = templates_dir

        self._selected_tile: str | None = None
        self._tile_buttons: dict[str, QPushButton] = {}
        self._slot_buttons: list[QPushButton] = []

        self.setWindowTitle("雀魂 AI · 牌面模板采集")
        self.setMinimumSize(720, 640)
        self._build_ui()
        self._refresh_progress()
        self._refresh_hand_slots()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_hand_slots)
        self._timer.start(800)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # 进度区
        prog_box = QGroupBox("采集进度")
        prog_layout = QVBoxLayout(prog_box)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(ALL_TEMPLATE_TILES))
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2d6a4f;")
        prog_layout.addWidget(self.progress_label)
        prog_layout.addWidget(self.progress_bar)
        hint = QLabel(
            "① 在雀魂对局中保持手牌可见  ② 点击下方缺失的牌名  ③ 再点右侧对应手牌槽位完成采集"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 11px;")
        prog_layout.addWidget(hint)
        root.addWidget(prog_box)

        body = QHBoxLayout()

        # 牌种网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QWidget()
        grid_layout = QVBoxLayout(grid_widget)

        for group_name, tiles in TILE_GROUPS:
            group = QGroupBox(group_name)
            g = QGridLayout(group)
            for i, tile in enumerate(tiles):
                btn = QPushButton(self._tile_button_text(tile))
                btn.setCheckable(True)
                btn.setMinimumHeight(36)
                btn.clicked.connect(lambda checked, t=tile: self._on_tile_selected(t))
                self._tile_buttons[tile] = btn
                g.addWidget(btn, i // 5, i % 5)
            grid_layout.addWidget(group)

        grid_layout.addStretch()
        scroll.setWidget(grid_widget)
        body.addWidget(scroll, stretch=3)

        # 手牌槽位
        slot_box = QGroupBox("当前手牌槽位（点击采集）")
        slot_layout = QVBoxLayout(slot_box)
        self.slot_info = QLabel("等待截图...")
        self.slot_info.setWordWrap(True)
        self.slot_info.setStyleSheet("font-family: Consolas; font-size: 11px;")
        slot_layout.addWidget(self.slot_info)

        slots_grid = QGridLayout()
        for i in range(14):
            btn = QPushButton(f"{i}")
            btn.setMinimumSize(44, 52)
            btn.clicked.connect(lambda checked, idx=i: self._on_slot_clicked(idx))
            self._slot_buttons.append(btn)
            slots_grid.addWidget(btn, i // 7, i % 7)
        slot_layout.addLayout(slots_grid)

        refresh_btn = QPushButton("立即刷新")
        refresh_btn.clicked.connect(self._refresh_hand_slots)
        slot_layout.addWidget(refresh_btn)
        body.addWidget(slot_box, stretch=2)

        root.addLayout(body)

        font = QFont("Microsoft YaHei UI", 9)
        self.setFont(font)

    def _tile_button_text(self, tile: str) -> str:
        u = TILE_UNICODE.get(tile, tile)
        name = TILE_NAMES_ZH.get(tile, tile)
        return f"{u}\n{tile}\n{name}"

    def _is_collected(self, tile: str) -> bool:
        return tile in self.recognizer._templates

    def _refresh_progress(self) -> None:
        collected = sum(1 for t in ALL_TEMPLATE_TILES if self._is_collected(t))
        total = len(ALL_TEMPLATE_TILES)
        self.progress_bar.setValue(collected)
        self.progress_label.setText(f"已采集 {collected} / {total}（{100 * collected // total}%）")

        for tile, btn in self._tile_buttons.items():
            done = self._is_collected(tile)
            if done:
                btn.setStyleSheet(
                    "QPushButton { background-color: #95d5b2; color: #1b4332; font-weight: bold; }"
                )
                btn.setToolTip("已采集")
            else:
                btn.setStyleSheet(
                    "QPushButton { background-color: #e9ecef; color: #495057; }"
                )
                btn.setToolTip("点击选中，再点手牌槽位采集")

            if self._selected_tile == tile:
                btn.setStyleSheet(
                    btn.styleSheet()
                    + " QPushButton { border: 3px solid #0077b6; }"
                )

    def _on_tile_selected(self, tile: str) -> None:
        if self._is_collected(tile):
            reply = QMessageBox.question(
                self, "重新采集",
                f"{tile} 已有模板，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._selected_tile = tile
        for t, btn in self._tile_buttons.items():
            btn.setChecked(t == tile)
        self._refresh_progress()
        self.setStatusTip(f"已选中 {tile}，请点击右侧手牌槽位")

    def _refresh_hand_slots(self) -> None:
        try:
            frame = self.capture_fn()
            if frame is None:
                self.slot_info.setText("未找到雀魂窗口")
                return
            aligned = self.align_fn(frame)
            slot_results = self.hand_slots_fn(aligned)
        except Exception as e:
            self.slot_info.setText(f"截图失败: {e}")
            return

        lines = []
        for tile, conf, idx in slot_results:
            if tile:
                lines.append(f"[{idx}] {TILE_UNICODE.get(tile, '')}{tile} {conf:.0%}")
            elif conf > 0:
                lines.append(f"[{idx}] ? {conf:.0%}")
        self.slot_info.setText("\n".join(lines) if lines else "（未检测到手牌）")

        detected_indices = {idx for _t, _c, idx in slot_results}
        for i, btn in enumerate(self._slot_buttons):
            if i in detected_indices:
                btn.setStyleSheet("background-color: #caf0f8;")
                btn.setText(f"{i}✓")
            else:
                btn.setStyleSheet("background-color: #f8f9fa;")
                btn.setText(str(i))

    def _on_slot_clicked(self, idx: int) -> None:
        if not self._selected_tile:
            QMessageBox.information(self, "提示", "请先在左侧选择要采集的牌种")
            return

        frame = self.capture_fn()
        if frame is None:
            QMessageBox.warning(self, "错误", "未找到雀魂窗口")
            return

        aligned = self.align_fn(frame)
        from majsoul_ai.vision.regions import detect_tile_in_slot

        crop = self._get_slot_crop(aligned, idx)
        if crop is None or not detect_tile_in_slot(crop):
            QMessageBox.warning(self, "错误", f"槽位 {idx} 未检测到牌")
            return

        tile = self._selected_tile
        path = self.recognizer.save_template(crop, tile)
        QMessageBox.information(self, "成功", f"已保存 {tile}\n{path}")
        self._selected_tile = None
        for btn in self._tile_buttons.values():
            btn.setChecked(False)
        self._refresh_progress()
        self._refresh_hand_slots()

    def set_regions(self, regions) -> None:
        self._regions = regions

    def _get_slot_crop(self, aligned, idx: int):
        if not hasattr(self, "_regions"):
            return None
        slots = self._regions.hand.slot_rects(self._regions.max_hand_slots)
        if idx < 0 or idx >= len(slots):
            return None
        return slots[idx].crop(aligned)


def run_template_collector(config_path: str | None = None) -> None:
    """启动图形化模板采集工具。"""
    from majsoul_ai.config import load_config
    from majsoul_ai.vision.align import ScreenAligner
    from majsoul_ai.vision.regions import RegionConfig
    from majsoul_ai.vision.tiles import TileRecognizer

    app = QApplication(sys.argv)

    if sys.platform != "win32":
        QMessageBox.critical(None, "错误", "模板采集需要在 Windows 上运行")
        sys.exit(1)

    from majsoul_ai.capture.window import WindowCapture

    cfg = load_config(config_path)
    capture = WindowCapture(cfg["window"]["title_keywords"])
    info = capture.find_window()
    if not info:
        QMessageBox.critical(None, "错误", "未找到雀魂窗口，请先启动游戏并进入对局")
        sys.exit(1)

    aligner = ScreenAligner(
        cfg["vision"]["standard_width"],
        cfg["vision"]["standard_height"],
        cfg["paths"].get("alignment_template"),
    )
    regions = RegionConfig.from_config(cfg["vision"])
    recognizer = TileRecognizer(cfg["paths"]["templates_dir"])

    def capture_fn():
        return capture.capture()

    def align_fn(frame):
        return aligner.transform(frame)

    def hand_slots_fn(aligned):
        return recognizer.recognize_hand(aligned, regions.hand, regions.max_hand_slots)

    win = TemplateCollectorWindow(
        recognizer, capture_fn, align_fn, hand_slots_fn, cfg["paths"]["templates_dir"]
    )
    win.set_regions(regions)
    win.show()
    sys.exit(app.exec())
