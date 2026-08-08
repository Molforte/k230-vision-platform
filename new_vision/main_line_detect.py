"""
main_line_detect.py — 巡线检测 (灰度 ROI)
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

# ── 巡线配置 ──
THRESHOLD   = 80       # 灰度阈值 (0-255), 低于=暗线
INVERT      = False    # False=暗线亮底, True=亮线暗底
ROI_Y_START = 0.55     # ROI 顶部比例 (0.55=底部 45%)
AUTO_THR    = False    # 自动阈值 (均值×0.7)
MIN_AREA    = 200
MIN_WIDTH   = 5

if not abort:
    from vision_modules.camera_utils import init_camera, init_display, deinit
    from vision_modules.line_detector import LineDetector
    from media.display import Display
    import cv2

    sensor  = init_camera(w=640, h=480)
    display = init_display(mode="lcd")

    ld = LineDetector(threshold=THRESHOLD, invert=INVERT,
                      roi_y_start=ROI_Y_START,
                      min_area=MIN_AREA, min_width=MIN_WIDTH,
                      auto_threshold=AUTO_THR)

    # ── 丢帧补偿配置 ──
    TARGET_MS   = 67
    MAX_FLUSH   = 4

    fc = time.clock()
    frame_n    = 0
    drop_total = 0
    drop_skip  = 0
    last_t     = 0

    print("Line detect. Ready. thr=%d inv=%d auto=%d" %
          (THRESHOLD, INVERT, AUTO_THR))

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

            r = ld.detect(np_img)
            ld.draw(np_img, r)

            cv2.putText(np_img, "fps=%.1f drop=%d" %
                        (fc.fps(), drop_total),
                        (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 1)

            Display.show_image(img)

            frame_n += 1
            if frame_n % 30 == 0:
                gc.collect()
    finally:
        deinit(sensor)
