"""运行时牌面识别监视窗口。"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from majsoul_ai.game.state_format import format_snapshot

if TYPE_CHECKING:
    from majsoul_ai.ai.mortal import AiRecommendation
    from majsoul_ai.game.snapshot import GameSnapshot


class RecognitionSignals(QObject):
    update = pyqtSignal(object, int, int)  # snapshot, template_count, template_total
    clear = pyqtSignal()


class RecognitionPanel(QWidget):
    """实时显示识别到的牌面信息，便于与游戏画面对照。"""

    def __init__(
        self,
        x: int = 500,
        y: int = 100,
        width: int = 420,
        height: int = 480,
        opacity: float = 0.94,
    ) -> None:
        super().__init__()
        self.setWindowTitle("牌面监视")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setGeometry(x, y, width, height)
        self.setWindowOpacity(opacity)
        self._drag_pos = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 20, 30, 245);
                border: 1px solid rgba(80, 120, 180, 200);
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("🔍 牌面识别监视")
        title.setStyleSheet("color: #7eb8ff; font-size: 13px; font-weight: bold; border: none;")
        layout.addWidget(title)

        sub = QLabel("对照游戏画面检查识别是否一致")
        sub.setStyleSheet("color: #8899aa; font-size: 10px; border: none;")
        layout.addWidget(sub)

        self.state_label = QLabel("等待识别...")
        self.state_label.setWordWrap(True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.state_label.setStyleSheet(
            "color: #e8ecf4; font-family: 'Microsoft YaHei UI', Consolas; "
            "font-size: 12px; line-height: 1.4; border: none; padding: 4px;"
        )
        layout.addWidget(self.state_label, stretch=1)

        self.setFont(QFont("Microsoft YaHei UI", 10))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def update_state(
        self,
        snap: "GameSnapshot | None",
        template_count: int = 0,
        template_total: int = 37,
    ) -> None:
        if snap is None:
            self.state_label.setText("等待识别...")
            return
        self.state_label.setText(format_snapshot(snap, template_count, template_total))

    def clear(self) -> None:
        self.state_label.setText("等待识别...")


class RecognitionPanelController:
    """牌面监视面板控制器（与 Overlay 同线程）。"""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.panel: RecognitionPanel | None = None
        self.signals = RecognitionSignals()

    def attach(self, app: QApplication) -> None:
        if not self.cfg.get("show_recognition_panel", True):
            return
        self.panel = RecognitionPanel(
            x=self.cfg.get("recognition_x", 500),
            y=self.cfg.get("recognition_y", 100),
            width=self.cfg.get("recognition_width", 420),
            height=self.cfg.get("recognition_height", 480),
            opacity=self.cfg.get("opacity", 0.92),
        )
        self.signals.update.connect(self._on_update)
        self.signals.clear.connect(self._on_clear)
        self.panel.show()

    def _on_update(self, snap, template_count, template_total):
        if self.panel:
            self.panel.update_state(snap, template_count, template_total)

    def _on_clear(self):
        if self.panel:
            self.panel.clear()

    def post_update(self, snap, template_count: int = 0, template_total: int = 37) -> None:
        self.signals.update.emit(snap, template_count, template_total)

    def post_clear(self) -> None:
        self.signals.clear.emit()
