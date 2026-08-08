"""
main_steel_ball_detect.py — K230 钢珠检测 + 多目标跟踪 + UART 输出

模型: yolo11n_det_320.kmodel (YOLO11n, 320x320, 单类 SteelBall)
输出: LCD 实时叠加 / UART2 (GPIO11/12 @115200) / REPL 串口
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

# ── 模型配置 ──
KMODEL_PATH      = "/sdcard/yolo11n_det_320.kmodel"
LABELS           = {0: 'SteelBall'}
MODEL_INPUT_SIZE = [320, 320]
RGB888P_SIZE     = [640, 360]
CONF_THRESH      = 0.6
NMS_THRESH       = 0.45

# ── 显示配置 ──
DISPLAY          = "lcd2_4"          # "hdmi" / "lcd3_5" / "lcd2_4"
if DISPLAY == "hdmi":
    DISPLAY_MODE = "hdmi"
    DISPLAY_SIZE = [1920, 1080]
elif DISPLAY == "lcd3_5":
    DISPLAY_MODE = "st7701"
    DISPLAY_SIZE = [800, 480]
else:  # lcd2_4
    DISPLAY_MODE = "st7701"
    DISPLAY_SIZE = [640, 480]

# ── 测距配置 ──
K_DIST           = 0.0               # 标定常数: dist_cm = K_DIST / ((w+h)/2)
DIST_MIN_CM      = 5.0
DIST_MAX_CM      = 150.0
EDGE_MARGIN      = 2

# ── 跟踪配置 ──
TRACK_SMOOTH_WIN = 5
TRACK_LOST_FRAMES = 5
TRACK_MATCH_GATE = 80
TRACK_N_MAX      = 5
TRACK_MAX_DETS_IN = 8
TRACK_MAX_TRACKS = 8
TRACK_MIN_HITS   = 2

# ── UART 配置 ──
UART_TX_PIN      = 11
UART_RX_PIN      = 12
UART_BAUD        = 115200
UART_SEND_DIV    = 1
REPL_PRINT       = True

# ── 显示颜色 (R,G,B) ──
CROSS_COLOR      = (255, 255, 0)
OK_COLOR         = (0, 255, 0)
BAD_COLOR        = (255, 0, 0)
TEXT_COLOR       = (255, 255, 255)


if not abort:
    from libs.PipeLine import PipeLine
    from libs.YOLO import YOLOv8
    from libs.Utils import *
    from media.sensor import *
    from machine import UART, FPIOA
    from vision_modules.uart_protocol import checksum, pack_frame, calc_flags
    from vision_modules.steel_ball_tracker import SteelBallTracker

    # ── 初始化管线 ──────────────────────────────────────

    pl = PipeLine(rgb888p_size=RGB888P_SIZE,
                  display_size=DISPLAY_SIZE,
                  display_mode=DISPLAY_MODE)
    if DISPLAY == "lcd2_4":
        pl.create(sensor=Sensor(id=2, width=1280, height=960))
    else:
        pl.create(sensor=Sensor(id=2, width=1920, height=1080))

    DISP_W, DISP_H = pl.get_display_size()
    CX, CY = DISP_W // 2, DISP_H // 2

    # ── 初始化检测器 ────────────────────────────────────

    yolo = YOLOv8(
        task_type="detect", mode="video",
        kmodel_path=KMODEL_PATH, labels=LABELS,
        rgb888p_size=RGB888P_SIZE,
        model_input_size=MODEL_INPUT_SIZE,
        display_size=[DISP_W, DISP_H],
        conf_thresh=CONF_THRESH, nms_thresh=NMS_THRESH,
        max_boxes_num=50, debug_mode=0,
    )
    yolo.config_preprocess()

    # ── 初始化跟踪器 ────────────────────────────────────

    tracker = SteelBallTracker(
        smooth_win=TRACK_SMOOTH_WIN, lost_frames=TRACK_LOST_FRAMES,
        match_gate=TRACK_MATCH_GATE, n_max=TRACK_N_MAX,
        max_tracks=TRACK_MAX_TRACKS, min_hits=TRACK_MIN_HITS,
    )

    # ── 初始化 UART ─────────────────────────────────────

    fpioa = FPIOA()
    fpioa.set_function(UART_TX_PIN, FPIOA.UART2_TXD)
    fpioa.set_function(UART_RX_PIN, FPIOA.UART2_RXD)
    uart = UART(UART.UART2, UART_BAUD)

    # ── LCD 叠加绘制 ────────────────────────────────────

    def draw_crosshair(osd):
        osd.draw_line(0, CY, DISP_W - 1, CY, color=CROSS_COLOR, thickness=1)
        osd.draw_line(CX, 0, CX, DISP_H - 1, color=CROSS_COLOR, thickness=1)
        osd.draw_circle(CX, CY, 6, color=CROSS_COLOR, thickness=1)

    def draw_target(osd, x, y, w, h, cx_i, cy_i, flags, dist_mm):
        color = OK_COLOR if (flags & 1) else BAD_COLOR
        osd.draw_cross(cx_i, cy_i, color=color, size=16, thickness=2)
        ty = y + h + 5
        if ty > DISP_H - 28:
            ty = DISP_H - 28
        txt = "D:%dcm" % (dist_mm // 10) if (flags & 1) else "D:---"
        osd.draw_string_advanced(x, ty, 24, txt, color=color)

    # ── 运行 ────────────────────────────────────────────

    fc = time.clock()
    frame_n = 0

    print("Steel ball detect ready. model=%s conf=%.2f disp=%dx%d" %
          (KMODEL_PATH, CONF_THRESH, DISP_W, DISP_H))

    try:
        while True:
            fc.tick()
            img = pl.get_frame()
            res = yolo.run(img)
            yolo.draw_result(res, pl.osd_img)

            # 1) 解析检测
            dets = []
            if res and len(res[0]) > 0:
                for i in range(len(res[0])):
                    x_f, y_f, w_f, h_f = res[0][i]
                    x_f = int(x_f); y_f = int(y_f)
                    w_f = int(w_f); h_f = int(h_f)
                    cx = x_f + w_f / 2.0
                    cy = y_f + h_f / 2.0
                    s  = (w_f + h_f) / 2.0
                    dist = K_DIST / s if (K_DIST > 0 and s > 0) else 0.0
                    dets.append((cx, cy, w_f, h_f, dist, w_f * h_f))
            # 面积降序 + 截断
            for i in range(1, len(dets)):
                cur = dets[i]; j = i - 1
                while j >= 0 and dets[j][5] < cur[5]:
                    dets[j + 1] = dets[j]; j -= 1
                dets[j + 1] = cur
            if len(dets) > TRACK_MAX_DETS_IN:
                dets = dets[:TRACK_MAX_DETS_IN]

            # 2) 跟踪 + 滑动平均
            out = tracker.update(dets)

            # 3) 逐目标计算输出量
            targets = []
            for t in out:
                cx_i = int(round(t['cx']));  cy_i = int(round(t['cy']))
                w_i  = int(round(t['w']));   h_i  = int(round(t['h']))
                x_i  = cx_i - w_i // 2;       y_i  = cy_i - h_i // 2
                dx   = cx_i - CX;             dy   = cy_i - CY
                flg, dmm = calc_flags(x_i, y_i, w_i, h_i, t['dist'],
                                      DISP_W, DISP_H, EDGE_MARGIN,
                                      K_DIST, DIST_MIN_CM, DIST_MAX_CM)
                targets.append((x_i, y_i, w_i, h_i, dx, dy, dmm, flg))

            # 4) LCD 叠加
            draw_crosshair(pl.osd_img)
            for tg in targets:
                draw_target(pl.osd_img, tg[0], tg[1], tg[2], tg[3],
                            tg[0] + tg[2] // 2, tg[1] + tg[3] // 2,
                            tg[7], tg[6])
            pl.osd_img.draw_string_advanced(
                4, 4, 24, "FPS:%d N:%d" % (int(fc.fps()), len(targets)),
                color=TEXT_COLOR)
            if K_DIST <= 0:
                pl.osd_img.draw_string_advanced(
                    4, 34, 32, "K NOT CALIBRATED!", color=BAD_COLOR)

            # 5) UART + REPL 输出
            frame = pack_frame(targets)
            if len(frame) > 200:
                frame = "$B,0*9E\r\n"
            frame_n += 1
            if frame_n % UART_SEND_DIV == 0:
                try:
                    uart.write(frame)
                except Exception:
                    pass
            if REPL_PRINT:
                print(frame[:-2])

            pl.show_image()

            if frame_n % 30 == 0:
                gc.collect()

    except KeyboardInterrupt:
        pass
    finally:
        yolo.deinit()
        pl.destroy()
