"""
main_color_detect.py — 纯颜色检测 (红/绿/蓝)
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
DS_W, DS_H = 160, 120         # 检测分辨率
SCALE     = 640 // DS_W       # 坐标缩放比

# ── 颜色配置 ──
COLORS   = ["red", "green", "blue"]
MIN_AREA = 200 // (SCALE * SCALE)   # 适配降采样后的面积阈值
EMA      = 0.5

if not abort:
    from vision_modules.camera_utils import init_camera, init_display, deinit
    from vision_modules.color_tracker import ColorTracker
    from media.display import Display
    import cv2

    sensor  = init_camera(w=640, h=480)
    display = init_display(mode="lcd")

    trackers = [ColorTracker(c, min_area=MIN_AREA, ema=EMA) for c in COLORS]

    # ── 丢帧补偿配置 ──
    TARGET_MS   = 67         # 目标帧间隔 ms (≈15fps)
    MAX_FLUSH   = 4          # 单次最多 flush 帧数

    fc = time.clock()
    frame_n    = 0
    drop_total = 0
    drop_skip  = 0
    last_t     = 0

    print("Color detect. Ready. colors=%s" % COLORS)

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

            # ── 降采样检测 (160x120) ──
            small = cv2.resize(np_img, (DS_W, DS_H))
            hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)

            total = 0
            for ct in trackers:
                blobs = ct.detect(hsv)
                # 坐标映射回 640x480 (含轮廓点)
                for b in blobs:
                    b["x"]  *= SCALE; b["y"]  *= SCALE
                    b["w"]  *= SCALE; b["h"]  *= SCALE
                    b["cx"] *= SCALE; b["cy"] *= SCALE
                    for i in range(len(b["cnt"])):
                        b["cnt"][i][0] *= SCALE
                        b["cnt"][i][1] *= SCALE
                    for i in range(len(b["approx"])):
                        b["approx"][i][0] *= SCALE
                        b["approx"][i][1] *= SCALE
                total += len(blobs)
                ct.draw(np_img, blobs)
                for b in blobs:
                    cv2.putText(np_img, ct.name,
                                (b["x"] + b["w"] + 4, b["y"] + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, ct.color, 2)

            cv2.putText(np_img, "fps=%.1f n=%d drop=%d" %
                        (fc.fps(), total, drop_total),
                        (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 1)

            Display.show_image(img)


            frame_n += 1
            if frame_n % 30 == 0:
                gc.collect()
    finally:
        deinit(sensor)
