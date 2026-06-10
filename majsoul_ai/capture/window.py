"""Windows 雀魂窗口捕捉。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Sequence

import numpy as np

if sys.platform == "win32":
    import win32gui
    import win32ui
    import win32con
    import win32api
else:
    win32gui = None  # type: ignore


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    left: int
    top: int
    width: int
    height: int


class WindowCapture:
    """通过 Win32 API 捕捉指定窗口的 BGR 图像。"""

    def __init__(self, title_keywords: Sequence[str]) -> None:
        if sys.platform != "win32":
            raise RuntimeError("窗口捕捉仅支持 Windows 平台")
        self.title_keywords = list(title_keywords)
        self._hwnd: int | None = None

    def find_window(self) -> WindowInfo | None:
        found: list[WindowInfo] = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if any(kw.lower() in title.lower() for kw in self.title_keywords):
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 200 and h > 200:
                    found.append(WindowInfo(hwnd, title, rect[0], rect[1], w, h))
            return True

        win32gui.EnumWindows(callback, None)
        if not found:
            return None
        # 优先选面积最大的窗口
        found.sort(key=lambda w: w.width * w.height, reverse=True)
        self._hwnd = found[0].hwnd
        return found[0]

    @property
    def hwnd(self) -> int | None:
        return self._hwnd

    def capture(self) -> np.ndarray | None:
        """返回 BGR numpy 数组，失败返回 None。"""
        if self._hwnd is None:
            info = self.find_window()
            if info is None:
                return None

        assert self._hwnd is not None
        if not win32gui.IsWindow(self._hwnd):
            self._hwnd = None
            return None

        left, top, right, bottom = win32gui.GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        hwnd_dc = win32gui.GetWindowDC(self._hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (height, width, 4)
        img = img[:, :, :3].copy()  # BGRA -> BGR

        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self._hwnd, hwnd_dc)

        return img

    def get_client_rect_screen(self) -> tuple[int, int, int, int] | None:
        """返回窗口客户区在屏幕上的 (left, top, width, height)。"""
        if self._hwnd is None:
            return None
        try:
            rect = win32gui.GetClientRect(self._hwnd)
            pt = win32gui.ClientToScreen(self._hwnd, (rect[0], rect[1]))
            return pt[0], pt[1], rect[2], rect[3]
        except Exception:
            return None
