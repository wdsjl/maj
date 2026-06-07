"""PyQt6 透明悬浮窗，显示 AI 出牌建议。"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
)

if TYPE_CHECKING:
    from majsoul_ai.ai.mortal import AiRecommendation


class OverlaySignals(QObject):
    update = pyqtSignal(object, str, list)  # recommendation, status, hand
    clear = pyqtSignal()


class OverlayWindow(QWidget):
    """始终置顶的半透明建议窗口。"""

    def __init__(
        self,
        x: int = 100,
        y: int = 100,
        width: int = 380,
        opacity: float = 0.92,
        always_on_top: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("雀魂 AI 助手")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(x, y, width, 220)
        self.setWindowOpacity(opacity)

        self._drag_pos = None
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget(self)
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: rgba(20, 24, 36, 230);
                border: 1px solid rgba(100, 140, 200, 180);
                border-radius: 12px;
            }
            QLabel { color: #e8ecf4; }
            QLabel#title { color: #7eb8ff; font-size: 13px; }
            QLabel#action { color: #ffd966; font-size: 18px; font-weight: bold; }
            QLabel#status { color: #8899aa; font-size: 11px; }
            QLabel#alt { color: #aab4c4; font-size: 12px; }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)

        title_row = QHBoxLayout()
        self.title_label = QLabel("🀄 雀魂 AI 助手")
        self.title_label.setObjectName("title")
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        self.status_label = QLabel("等待雀魂窗口...")
        self.status_label.setObjectName("status")
        title_row.addWidget(self.status_label)
        layout.addLayout(title_row)

        self.action_label = QLabel("—")
        self.action_label.setObjectName("action")
        self.action_label.setWordWrap(True)
        layout.addWidget(self.action_label)

        self.hand_label = QLabel("")
        self.hand_label.setObjectName("alt")
        self.hand_label.setWordWrap(True)
        layout.addWidget(self.hand_label)

        self.alt_label = QLabel("")
        self.alt_label.setObjectName("alt")
        self.alt_label.setWordWrap(True)
        layout.addWidget(self.alt_label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        font = QFont("Microsoft YaHei UI", 10)
        self.setFont(font)

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

    def show_recommendation(
        self,
        recommendation: "AiRecommendation | None",
        status: str = "",
        hand_display: str = "",
    ) -> None:
        if recommendation:
            prefix = "⚠️ [简易模式] " if recommendation.raw.get("_fallback") else "✅ "
            self.action_label.setText(prefix + recommendation.action_text)
            if recommendation.alternatives:
                lines = []
                for name, weight in recommendation.alternatives[:3]:
                    pct = weight * 100
                    lines.append(f"  · {name}  {pct:.1f}%")
                self.alt_label.setText("备选:\n" + "\n".join(lines))
            else:
                self.alt_label.setText("")
        else:
            self.action_label.setText("—")
            self.alt_label.setText("")

        self.hand_label.setText(f"手牌: {hand_display}" if hand_display else "")
        if status:
            self.status_label.setText(status)

    def clear(self) -> None:
        self.action_label.setText("—")
        self.alt_label.setText("")
        self.hand_label.setText("")


class OverlayController:
    """在独立线程中运行 Qt 事件循环。"""

    def __init__(self, overlay_cfg: dict) -> None:
        self.cfg = overlay_cfg
        self.app: QApplication | None = None
        self.window: OverlayWindow | None = None
        self.signals = OverlaySignals()

    def run(self) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = OverlayWindow(
            x=self.cfg.get("x", 100),
            y=self.cfg.get("y", 100),
            width=self.cfg.get("width", 380),
            opacity=self.cfg.get("opacity", 0.92),
        )
        self.signals.update.connect(self._on_update)
        self.signals.clear.connect(self._on_clear)
        self.window.show()
        self.app.exec()

    def _on_update(self, recommendation, status, hand):
        if self.window:
            self.window.show_recommendation(recommendation, status, hand)

    def _on_clear(self):
        if self.window:
            self.window.clear()

    def post_update(self, recommendation, status: str = "", hand_display: str = "") -> None:
        self.signals.update.emit(recommendation, status, hand_display)

    def post_clear(self) -> None:
        self.signals.clear.emit()
