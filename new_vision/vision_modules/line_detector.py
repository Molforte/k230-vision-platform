"""
line_detector.py — 巡线检测 (ROI 二值化 + 轮廓分析)

原理:
    图像底部 ROI → 灰度 → 阈值二值化 → 最大轮廓 → 质心 + 偏角
    输出归一化偏差信号 (-1.0..1.0), 可直接喂 PID

使用:
    ld = LineDetector(threshold=100)
    r = ld.detect(np_img)
    if r["valid"]:
        steering = r["deviation"]   # -1.0=左满舵, 0=正中, +1.0=右满舵
"""
import cv2, math
from ulab import numpy as np

_K_OPEN = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


class LineDetector:

    def __init__(self, threshold=100, invert=False,
                 roi_y_start=0.55, min_area=200, min_width=5,
                 auto_threshold=False):
        self.threshold   = threshold
        self.invert      = invert        # True=亮线暗底
        self.roi_start   = roi_y_start   # ROI 顶部比例
        self.min_area    = min_area
        self.min_width   = min_width
        self.auto_thr    = auto_threshold
        self._img_w = self._img_h = 0

    # ── 检测 ──────────────────────────────────────────────
    def detect(self, np_img):
        h, w = np_img.shape[:2]
        self._img_w, self._img_h = w, h

        # ROI: 图像底部
        ry = int(h * self.roi_start)
        rh = h - ry
        roi = np_img[ry:h, 0:w]

        # 灰度 + 阈值
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        if self.auto_thr:
            mean_v = np.mean(gray)
            thr = int(mean_v * 0.7)
        else:
            thr = self.threshold

        _, binary = cv2.threshold(gray, thr, 255,
                    cv2.THRESH_BINARY if self.invert else cv2.THRESH_BINARY_INV)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, _K_OPEN)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._empty()

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best = contours[0]
        area = cv2.contourArea(best)
        if area < self.min_area:
            return self._empty()

        M = cv2.moments(best)
        if M["m00"] == 0:
            return self._empty()

        lx = M["m10"] / M["m00"]
        ly = M["m01"] / M["m00"]

        # 线宽估算
        _, _, _, bh = cv2.boundingRect(best)
        line_w = float(area) / max(float(bh), 1.0)
        if line_w < self.min_width:
            return self._empty()

        # 方向角 (minAreaRect)
        rect = cv2.minAreaRect(best)
        angle = rect[2]
        if rect[1][0] < rect[1][1]:
            angle += 90.0
        if angle > 90:
            angle -= 180
        if angle < -90:
            angle += 180

        abs_cx = lx
        abs_cy = ry + ly

        deviation = (abs_cx - w / 2.0) / (w / 2.0)
        deviation = max(-1.0, min(1.0, deviation))

        return {
            "valid":     True,
            "cx":        abs_cx,
            "cy":        abs_cy,
            "deviation": deviation,
            "angle":     angle,
            "width":     line_w,
            "area":      area,
            "contour":   best,
            "roi":       (0, ry, w, rh),
        }

    # ── 绘制 ──────────────────────────────────────────────
    def draw(self, np_img, result, color=(0, 255, 0)):
        rx, ry, rw, rh = result["roi"]
        # ROI 框
        cv2.rectangle(np_img, (rx, ry), (rx + rw, ry + rh), (128, 128, 128), 1)

        if not result["valid"]:
            return

        # 线轮廓
        c = result["contour"]
        shifted = c.copy()
        for i in range(len(shifted)):
            shifted[i][1] += ry
        cv2.drawContours(np_img, [shifted], -1, color, 2)

        # 中心十字
        cx, cy = int(result["cx"]), int(result["cy"])
        cv2.line(np_img, (cx - 8, cy), (cx + 8, cy), (0, 0, 255), 2)
        cv2.line(np_img, (cx, cy - 8), (cx, cy + 8), (0, 0, 255), 2)

        # 偏差条 (底部)
        dev = result["deviation"]
        bar_y = int(self._img_h * 0.95)
        mid_x = self._img_w // 2
        cv2.line(np_img, (0, bar_y), (self._img_w, bar_y), (64, 64, 64), 1)
        cv2.circle(np_img, (mid_x, bar_y), 4, (0, 255, 0), -1)
        dot_x = int(mid_x + dev * mid_x * 0.8)
        cv2.circle(np_img, (dot_x, bar_y), 6, (0, 0, 255), -1)

        # 标注
        w = self._img_w
        cv2.putText(np_img, "dev=%.2f ang=%.0f" % (dev, result["angle"]),
                    (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

    # ── helpers ───────────────────────────────────────────
    def _empty(self):
        ry = int(self._img_h * self.roi_start)
        rh = self._img_h - ry
        return {
            "valid": False, "cx": 0, "cy": 0,
            "deviation": 0, "angle": 0, "width": 0, "area": 0,
            "contour": None, "roi": (0, ry, self._img_w, rh),
        }
