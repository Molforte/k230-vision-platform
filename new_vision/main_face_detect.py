"""
main_face_detect.py — K230 人脸检测 (双通道: ch0 显示, ch2 KPU)

ch0: RGB888 → Display.show_image() → LCD + IDE
ch2: RGBP888 → KPU 推理

前置准备（SD 卡文件）:
  /sdcard/kmodel/face_detection_320.kmodel     ← 模型
  /sdcard/utils/prior_data_320.bin             ← 锚点
"""

import time, gc
from media.sensor import Sensor
from media.display import Display
from vision_modules.face_detector import FaceDetector
import ulab.numpy as np

# ============================================================
# 配置
# ============================================================

KMODEL_PATH   = "/sdcard/kmodel/face_detection_320.kmodel"
ANCHORS_PATH  = "/sdcard/utils/prior_data_320.bin"

SENSOR_W, SENSOR_H = 640, 480      # 横屏，ST7701 竖屏会有黑边
AI_W, AI_H         = 640, 360      # AI 通道
MODEL_INPUT_SIZE   = [320, 320]
CONF_THRES         = 0.5
NMS_THRES          = 0.2
ANCHOR_LEN         = 4200
DET_DIM            = 4

CAM_CHN_ID_0 = 0   # 显示通道
CAM_CHN_ID_2 = 2   # AI 通道

# ============================================================
# 加载锚点
# ============================================================

anchors = np.fromfile(ANCHORS_PATH, dtype=np.float)
anchors = anchors.reshape((ANCHOR_LEN, DET_DIM))

# ============================================================
# 初始化 sensor (双通道)
# ============================================================

sensor = Sensor(fps=30)
sensor.reset()

# ch0: 显示 → RGB888
sensor.set_framesize(w=SENSOR_W, h=SENSOR_H, chn=CAM_CHN_ID_0)
sensor.set_pixformat(Sensor.RGB888, chn=CAM_CHN_ID_0)

# ch2: AI → RGBP888 (planar, KPU 需要)
sensor.set_framesize(w=AI_W, h=AI_H, chn=CAM_CHN_ID_2)
sensor.set_pixformat(Sensor.RGBP888, chn=CAM_CHN_ID_2)

sensor.run()
time.sleep(0.3)

# ============================================================
# 初始化显示器
# ============================================================

Display.init(Display.ST7701, to_ide=True)

# ============================================================
# 初始化检测器
# ============================================================

detector = FaceDetector(
    kmodel_path=KMODEL_PATH,
    anchors=anchors,
    model_input_size=MODEL_INPUT_SIZE,
    confidence_threshold=CONF_THRES,
    nms_threshold=NMS_THRES,
    rgb888p_size=[AI_W, AI_H],
    display_size=[SENSOR_W, SENSOR_H],
    debug_mode=0,
)
detector.config_preprocess()

sc_x = SENSOR_W / AI_W
sc_y = SENSOR_H / AI_H

print(f"Face detection ready.  AI={AI_W}x{AI_H}  disp={SENSOR_W}x{SENSOR_H}  conf={CONF_THRES:.2f}")

# ============================================================
# 主循环
# ============================================================

fc = time.clock()
frame_n = 0

try:
    while True:
        fc.tick()
        ai_img = sensor.snapshot(chn=CAM_CHN_ID_2)
        np_img = ai_img.to_numpy_ref()
        dets = detector.run(np_img)

        # ch0 → 显示
        disp_img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 在显示图像上画框
        if dets:
            for det in dets:
                x, y, w, h = map(lambda v: int(round(v, 0)), det[:4])
                x = int(x * sc_x)
                y = int(y * sc_y)
                w = int(w * sc_x)
                h = int(h * sc_y)
                disp_img.draw_rectangle(x, y, w, h,
                                        color=(255, 255, 0), thickness=2)

        Display.show_image(disp_img)

        frame_n += 1
        if frame_n % 30 == 0:
            gc.collect()
finally:
    detector.deinit()
    sensor.stop()
    Display.deinit()
