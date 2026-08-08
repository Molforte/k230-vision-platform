"""
camera_utils.py — 摄像头与显示器初始化 (CanMV K230)

参考: canmv_k230-canmv_k230/resources/examples/
"""
import time
from media.sensor import Sensor
from media.display import Display


FMT_RGB888 = Sensor.RGB888
FMT_RGB565 = Sensor.RGB565
FMT_GRAY   = Sensor.GRAYSCALE

LCD  = "lcd"
HDMI = "hdmi"
IDE  = "ide"


def init_camera(w=640, h=480, fmt=None, hm=False, vf=False):
    if fmt is None:
        fmt = Sensor.RGB888
    sensor = Sensor(width=w, height=h)
    sensor.reset()
    sensor.set_framesize(width=w, height=h)
    sensor.set_pixformat(fmt)
    if hm:
        sensor.set_hmirror(True)
    if vf:
        sensor.set_vflip(True)
    sensor.run()
    time.sleep(0.3)
    return sensor


def init_display(mode=IDE, w=640, h=480, to_ide=True):
    m = mode.lower()
    if m == IDE:
        Display.init(Display.VIRT, width=w, height=h, to_ide=to_ide)
    elif m == LCD:
        Display.init(Display.ST7701, to_ide=to_ide)
    elif m == HDMI:
        Display.init(Display.LT9611, width=w, height=h, to_ide=to_ide)
    else:
        Display.init(Display.ST7701, to_ide=to_ide)
    return Display


def deinit(sensor=None):
    if sensor is not None:
        try:
            sensor.stop()
        except Exception:
            pass
    try:
        Display.deinit()
    except Exception:
        pass
