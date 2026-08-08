"""
color_shape_detector.py — 颜色+形状联合检测

管线: RGB → HSV → 多色 inRange → 形态学 → findContours → approxPolyDP 形状分类
"""
import cv2, math
from ulab import numpy as np

# ── 电赛 HSV 范围 ──
_HSV = {
    "red":    ([0,   140, 120], [10,  255, 255]),
    "red2":   ([170, 140, 120], [180, 255, 255]),
    "green":  ([35,  60,  60],  [85,  255, 255]),
    "blue":   ([90,  90,  90],  [130, 255, 255]),
}

_DRAW = {
    "red":   (255, 0, 0),
    "green": (0, 255, 0),
    "blue":  (0, 0, 255),
}

_K_OPEN  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
_K_CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


# ── 形状分类 ────────────────────────────────────────────
def _classify(blob):
    """blob = {cnt, approx, area, w, h} → "triangle"|"rectangle"|"circle"|"irregular" """
    n = len(blob["approx"])
    if n == 3:
        return "triangle"
    if n == 4:
        return "rectangle"
    if n >= 8:
        w, h = blob["w"], blob["h"]
        ratio = w / h if h else 0
        if 0.75 < ratio < 1.35:
            peri = cv2.arcLength(blob["cnt"], True)
            if peri > 0:
                c = 4 * math.pi * blob["area"] / (peri * peri)
                if c > 0.70:
                    return "circle"
    return "irregular"


# ── 检测器 ──────────────────────────────────────────────
class ColorShapeDetector:

    def __init__(self, colors=None, min_area=200):
        if colors is None:
            colors = ["red", "green", "blue"]
        self.colors  = colors
        self.min_a   = min_area

    def detect(self, np_img):
        """
        np_img: RGB/BGR numpy array (任意分辨率)
        返回 [{color,shape,x,y,w,h,cx,cy,area,approx,cnt}, ...]
        """
        hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)
        results = []

        for name in self.colors:
            lo = np.array(_HSV[name][0], dtype=np.uint8)
            hi = np.array(_HSV[name][1], dtype=np.uint8)
            m  = cv2.inRange(hsv, lo, hi)
            if name == "red":
                lo2 = np.array(_HSV["red2"][0], dtype=np.uint8)
                hi2 = np.array(_HSV["red2"][1], dtype=np.uint8)
                m = cv2.bitwise_or(m, cv2.inRange(hsv, lo2, hi2))
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  _K_OPEN)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, _K_CLOSE)

            contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                a = cv2.contourArea(c)
                if a < self.min_a:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                p  = cv2.arcLength(c, True)
                ap = cv2.approxPolyDP(c, 0.03 * p, True)
                blob = {"cnt": c, "approx": ap, "area": a, "w": w, "h": h}
                shape = _classify(blob)
                if shape == "irregular":
                    continue
                results.append({
                    "color": name,
                    "shape": shape,
                    "x": x, "y": y, "w": w, "h": h,
                    "cx": x + w // 2, "cy": y + h // 2,
                    "area": a,
                    "approx": ap,
                    "cnt": c,
                })

        return results

    # ── 绘制 ──────────────────────────────────────────
    def draw(self, np_img, targets):
        for t in targets:
            c = _DRAW.get(t["color"], (255, 255, 0))
            cv2.rectangle(np_img, (t["x"], t["y"]),
                          (t["x"] + t["w"], t["y"] + t["h"]), c, 2)
            cv2.drawContours(np_img, [t["approx"]], -1, c, 2)
            label = "%s-%s" % (t["color"], t["shape"])
            cv2.putText(np_img, label,
                        (t["x"], t["y"] - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2)
