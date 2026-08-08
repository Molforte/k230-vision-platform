"""
main_color_shape_detect.py — 颜色+形状联合检测
"""
import time, gc

try:
    from ybUtils.YbKey import YbKey
except ImportError:
    class YbKey:
        def is_pressed(self): return False

key = YbKey()
abort = 0
if key.is_pressed():
    time.sleep_ms(10)
    if key.is_pressed():
        abort = 1

# ── 降采样加速 ──
DS_W, DS_H = 160, 120
SCALE     = 640 // DS_W

# ── 检测配置 ──
COLORS   = ["red", "green", "blue"]
MIN_AREA = 200 // (SCALE * SCALE)

if not abort:
    from vision_modules.camera_utils import init_camera, init_display, deinit
    from vision_modules.color_shape_detector import ColorShapeDetector
    from media.display import Display
    import cv2

    sensor  = init_camera(w=640, h=480)
    display = init_display(mode="lcd")

    csd = ColorShapeDetector(colors=COLORS, min_area=MIN_AREA)

    # ── 丢帧补偿配置 ──
    TARGET_MS   = 67         # 目标帧间隔 ms (≈15fps)
    MAX_FLUSH   = 4          # 单次最多 flush 帧数

    fc = time.clock()
    frame_n    = 0
    drop_total = 0
    drop_skip  = 0
    last_t     = 0

    # ── 帧间暂留 (防深色偶发丢目标) ──
    HOLD_FRAMES = 2         # 消失 ≤N 帧仍显示
    MATCH_D2    = 400       # 匹配距离² (20² at 160x120)
    prev_stale  = []        # [{color,shape,cx,cy,miss,...}, ...]

    print("Color+Shape detect. Ready. colors=%s" % COLORS)

    try:
        while True:
            fc.tick()

            # ── 丢帧补偿 ──
            now = time.ticks_ms()
            if last_t != 0:
                elapsed = time.ticks_diff(now, last_t)
                if elapsed > TARGET_MS * 1.2:
                    dropped = max(0, elapsed // TARGET_MS - 1)
                    drop_total += dropped
                    flush_n = min(dropped, MAX_FLUSH)
                    for _ in range(flush_n):
                        sensor.snapshot()
                    drop_skip += flush_n
            last_t = now

            img = sensor.snapshot()
            np_img = img.to_numpy_ref()

            # ── 降采样检测 ──
            small = cv2.resize(np_img, (DS_W, DS_H))
            targets = csd.detect(small)

            # ── 坐标映射 + 绘制 ──
            for t in targets:
                t["x"]  *= SCALE; t["y"]  *= SCALE
                t["w"]  *= SCALE; t["h"]  *= SCALE
                t["cx"] *= SCALE; t["cy"] *= SCALE
                for i in range(len(t["cnt"])):
                    t["cnt"][i][0] *= SCALE
                    t["cnt"][i][1] *= SCALE
                for i in range(len(t["approx"])):
                    t["approx"][i][0] *= SCALE
                    t["approx"][i][1] *= SCALE

            # ── 帧间暂留: 补齐偶发丢帧的目标 ──
            for p in prev_stale:
                p["_m"] = False
            # 当前目标 → 匹配上帧
            for t in targets:
                best, best_d2 = None, MATCH_D2 * SCALE * SCALE + 1
                for p in prev_stale:
                    if p["_m"] or p["color"] != t["color"] or p["shape"] != t["shape"]:
                        continue
                    d2 = (t["cx"] - p["cx"]) ** 2 + (t["cy"] - p["cy"]) ** 2
                    if d2 < best_d2:
                        best_d2 = d2
                        best = p
                if best is not None:
                    best["_m"] = True
            # 未匹配的上帧目标: miss+1, ≤HOLD_FRAMES 则保留
            next_stale = []
            for t in targets:
                next_stale.append({"color": t["color"], "shape": t["shape"],
                    "cx": t["cx"], "cy": t["cy"], "x": t["x"], "y": t["y"],
                    "w": t["w"], "h": t["h"], "approx": t["approx"],
                    "cnt": t["cnt"], "miss": 0})
            for p in prev_stale:
                if not p["_m"]:
                    p["miss"] += 1
                    if p["miss"] <= HOLD_FRAMES:
                        del p["_m"]
                        targets.append(p)
                        next_stale.append(p)
            prev_stale = next_stale

            csd.draw(np_img, targets)

            cv2.putText(np_img, "fps=%.1f n=%d drop=%d" %
                        (fc.fps(), len(targets), drop_total),
                        (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 1)

            Display.show_image(img)


            frame_n += 1
            if frame_n % 30 == 0:
                gc.collect()
    finally:
        deinit(sensor)
