"""
color_tracker.py — 电赛纯色检测 (红/绿/蓝)

电赛参考: 2020-G 非接触物体尺寸形态测量
  目标物颜色: 红、绿、蓝纯色
"""
import cv2
from ulab import numpy as np

# ── 电赛三色 HSV 范围 ──
# 红: hue 绕 0°, 两段 mask 合并
HSV = {
    "red":    ([0,   140, 120], [10,  255, 255]),
    "red2":   ([170, 140, 120], [180, 255, 255]),
    "green":  ([35,  60,  60],  [85,  255, 255]),
    "blue":   ([90,  90,  90],  [130, 255, 255]),
}

DRAW = {
    "red":   (255, 0, 0),
    "green": (0, 255, 0),
    "blue":  (0, 0, 255),
}

# 形态学核 (去噪)
_K_CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
_K_OPEN  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


class ColorTracker:

    def __init__(self, name, min_area=200, ema=0.5):
        name = name.lower()
        if name not in HSV:
            raise ValueError("unknown color: %s (choices: red/green/blue)" % name)
        self.name   = name
        self._red   = (name == "red")
        self.ema    = ema
        self.min_a  = min_area
        lo, hi      = HSV[name]
        self.lo     = np.array(lo, dtype=np.uint8)
        self.hi     = np.array(hi, dtype=np.uint8)
        self.color  = DRAW[name]
        self._cx = self._cy = self._w = self._h = None

    # ── 检测 ──────────────────────────────────────────────
    def detect(self, hsv_np):
        """返回 blob 列表 [{cnt,approx,x,y,w,h,area,cx,cy},...] 按面积降序"""
        m = cv2.inRange(hsv_np, self.lo, self.hi)
        if self._red:
            lo2 = np.array(HSV["red2"][0], dtype=np.uint8)
            hi2 = np.array(HSV["red2"][1], dtype=np.uint8)
            m = cv2.bitwise_or(m, cv2.inRange(hsv_np, lo2, hi2))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  _K_OPEN)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, _K_CLOSE)

        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for c in contours:
            a = cv2.contourArea(c)
            if a < self.min_a:
                continue
            x, y, w, h = cv2.boundingRect(c)
            p  = cv2.arcLength(c, True)
            ap = cv2.approxPolyDP(c, 0.03 * p, True)
            out.append({"cnt": c, "approx": ap,
                        "x": x, "y": y, "w": w, "h": h,
                        "area": a, "cx": x + w // 2, "cy": y + h // 2})
        out.sort(key=lambda o: o["area"], reverse=True)

        # EMA 平滑 (最近邻匹配, 防止相邻同色目标间跳变)
        if out and self.ema > 0:
            if self._cx is not None:
                # 找离上帧位置最近的 blob
                best = out[0]
                best_d2 = (best["cx"] - self._cx) ** 2 + (best["cy"] - self._cy) ** 2
                for b in out[1:]:
                    d2 = (b["cx"] - self._cx) ** 2 + (b["cy"] - self._cy) ** 2
                    if d2 < best_d2:
                        best_d2 = d2
                        best = b
                b = best
                k = self.ema
                b["cx"] = int(k * self._cx + (1 - k) * b["cx"])
                b["cy"] = int(k * self._cy + (1 - k) * b["cy"])
                b["w"]  = int(k * self._w  + (1 - k) * b["w"])
                b["h"]  = int(k * self._h  + (1 - k) * b["h"])
                b["x"]  = b["cx"] - b["w"] // 2
                b["y"]  = b["cy"] - b["h"] // 2
            else:
                b = out[0]   # 首帧: 取最大面积初始化
            self._cx, self._cy = b["cx"], b["cy"]
            self._w,  self._h  = b["w"],  b["h"]
        return out

    # ── 绘制 ──────────────────────────────────────────────
    def draw(self, np_img, blobs):
        for b in blobs:
            cv2.rectangle(np_img, (b["x"], b["y"]),
                          (b["x"] + b["w"], b["y"] + b["h"]), self.color, 2)
            cv2.drawContours(np_img, [b["approx"]], -1, self.color, 2)

    # ── 重置 EMA ──────────────────────────────────────────
    def reset(self):
        self._cx = self._cy = self._w = self._h = None
