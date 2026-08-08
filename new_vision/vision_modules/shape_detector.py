"""
shape_detector.py — 最简形状检测
"""
import cv2, math

_SHAPE_COLORS = {
    "triangle":  (255, 0, 255),
    "rectangle": (0, 0, 255),
    "circle":    (0, 255, 0),
}


def classify_shape(blob):
    n = len(blob["approx"])
    if n == 3:
        return "triangle"
    if n == 4:
        return "rectangle"
    if n >= 8:
        area = blob["area"]
        w, h = blob["w"], blob["h"]
        ratio = w / h if h else 0
        if 0.75 < ratio < 1.35:
            peri = cv2.arcLength(blob["cnt"], True)
            if peri > 0:
                c = 4 * math.pi * area / (peri * peri)
                if c > 0.70:
                    return "circle"
    return "irregular"


class ShapeDetector:

    def __init__(self, min_area=500, canny_low=30, canny_high=100, blur=7):
        self.min_area = min_area
        self._canny_lo = canny_low
        self._canny_hi = canny_high
        self._blur = blur

    def detect(self, np_img):
        gray = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self._blur, self._blur), 0)
        edges = cv2.Canny(gray, self._canny_lo, self._canny_hi)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        results = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
            blob = {"approx": approx, "area": area, "w": w, "h": h, "cnt": cnt}
            shape = classify_shape(blob)
            if shape == "irregular":
                continue
            results.append({
                "approx": approx,
                "x": x, "y": y, "w": w, "h": h,
                "cx": x + w // 2, "cy": y + h // 2,
                "shape": shape,
            })

        return results

    def classify(self, blob):
        return classify_shape(blob)

    def draw(self, np_img, shapes):
        if not shapes:
            return
        for s in shapes:
            approx = s.get("approx", [])
            if not approx:
                continue
            color = _SHAPE_COLORS.get(s["shape"], (0, 255, 255))
            cv2.drawContours(np_img, [approx], -1, color, 3)
            cv2.putText(np_img, s["shape"],
                        (s["cx"] - 15, s["cy"]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
