"""画面配准：将任意窗口截图变换到标准 1280x720 坐标系。"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ScreenAligner:
    """
    使用 ORB 特征匹配 + RANSAC 单应性矩阵，将截图对齐到标准坐标。
    若配准失败，则使用 letterbox 缩放作为回退。
    """

    def __init__(
        self,
        standard_w: int = 1280,
        standard_h: int = 720,
        alignment_template_path: str | None = None,
    ) -> None:
        self.standard_w = standard_w
        self.standard_h = standard_h
        self._matrix: np.ndarray | None = None
        self._orb = cv2.ORB_create(5000)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        self._template_kp = None
        self._template_desc = None
        self._template_gray: np.ndarray | None = None

        if alignment_template_path and Path(alignment_template_path).exists():
            tpl = cv2.imread(alignment_template_path)
            if tpl is not None:
                self._template_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
                self._template_kp, self._template_desc = self._orb.detectAndCompute(
                    self._template_gray, None
                )

    @property
    def is_calibrated(self) -> bool:
        return self._matrix is not None

    def calibrate(self, frame_bgr: np.ndarray) -> bool:
        """从当前帧计算变换矩阵。"""
        if self._template_gray is None:
            return self._calibrate_letterbox(frame_bgr)

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        kp, desc = self._orb.detectAndCompute(gray, None)
        if desc is None or self._template_desc is None:
            return self._calibrate_letterbox(frame_bgr)

        matches = self._matcher.knnMatch(desc, self._template_desc, k=2)
        good = []
        for pair in matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < 0.75 * n.distance:
                    good.append(m)

        if len(good) < 8:
            return self._calibrate_letterbox(frame_bgr)

        src_pts = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([self._template_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        matrix, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if matrix is None:
            return self._calibrate_letterbox(frame_bgr)

        self._matrix = matrix
        return True

    def _calibrate_letterbox(self, frame_bgr: np.ndarray) -> bool:
        """无模板时使用等比缩放 + 黑边填充。"""
        h, w = frame_bgr.shape[:2]
        scale = min(self.standard_w / w, self.standard_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        offset_x = (self.standard_w - new_w) / 2
        offset_y = (self.standard_h - new_h) / 2
        self._matrix = np.array(
            [
                [scale, 0, offset_x],
                [0, scale, offset_y],
                [0, 0, 1],
            ],
            dtype=np.float64,
        )
        return True

    def transform(self, frame_bgr: np.ndarray) -> np.ndarray:
        """将帧变换到标准坐标系。"""
        if self._matrix is None:
            self.calibrate(frame_bgr)
        assert self._matrix is not None
        return cv2.warpPerspective(
            frame_bgr,
            self._matrix,
            (self.standard_w, self.standard_h),
            flags=cv2.INTER_LINEAR,
        )

    def reset(self) -> None:
        self._matrix = None
