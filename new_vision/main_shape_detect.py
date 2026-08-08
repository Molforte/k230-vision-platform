"""
main_shape_detect.py — 独立形状检测
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

if not abort:
    from vision_modules.camera_utils import init_camera, init_display, deinit
    from vision_modules.shape_detector import ShapeDetector
    from media.display import Display
    import cv2

    sensor  = init_camera(w=640, h=480)
    display = init_display(mode="lcd")

    sd = ShapeDetector(min_area=500, canny_low=30, canny_high=100, blur=7)

    # ── 丢帧补偿配置 ──
    TARGET_MS   = 67         # 目标帧间隔 ms (≈15fps)
    MAX_FLUSH   = 4          # 单次最多 flush 帧数

    fc = time.clock()
    frame_n    = 0
    drop_total = 0           # 累计丢帧
    drop_skip  = 0           # 补偿跳帧次数
    last_t     = 0           # 上帧时间戳 (ticks_ms)

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

            shapes = sd.detect(np_img)
            sd.draw(np_img, shapes)

            cv2.putText(np_img, "fps=%.1f n=%d drop=%d" %
                        (fc.fps(), len(shapes), drop_total),
                        (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 1)
            Display.show_image(img)

            frame_n += 1
            if frame_n % 30 == 0:
                gc.collect()
    finally:
        deinit(sensor)
