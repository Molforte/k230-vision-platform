"""
face_detector.py — K230 人脸检测模块

基于 anchor-based 人脸检测模型 (face_detection_320.kmodel, 320×320)。
依赖 aidemo.face_det_post_process 做后处理。

用法:
    from vision_modules.face_detector import FaceDetector
    detector = FaceDetector(kmodel_path, anchors, ...)
    detector.config_preprocess()
    res = detector.run(img)
    detector.draw_result(pl, res)
"""

from libs.AIBase import AIBase
from libs.AI2D import Ai2d
from libs.Utils import ScopedTiming, letterbox_pad_param
import nncase_runtime as nn
import ulab.numpy as np
import aidemo
from media.media import *


class FaceDetector(AIBase):
    """
    K230 人脸检测器。

    kmodel_path : str               — kmodel 模型路径
    anchors     : np.ndarray        — 锚点 (4200, 4)
    model_input_size  : list[2]     — 模型输入尺寸, 默认 [320, 320]
    confidence_threshold : float    — 置信度阈值
    nms_threshold        : float    — NMS 阈值
    rgb888p_size : list[2]          — sensor 输入分辨率, 默认 [640, 360]
    display_size : list[2]          — 显示分辨率, 默认 [640, 480]
    debug_mode   : int              — 0 关闭, >0 开启计时打印
    """

    def __init__(self, kmodel_path, anchors,
                 model_input_size=None,
                 confidence_threshold=0.5, nms_threshold=0.2,
                 rgb888p_size=None, display_size=None,
                 debug_mode=0):
        if model_input_size is None:
            model_input_size = [320, 320]
        if rgb888p_size is None:
            rgb888p_size = [640, 360]
        if display_size is None:
            display_size = [640, 480]

        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)

        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.anchors = anchors
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode

        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(
            nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
            np.uint8, np.uint8
        )

    def config_preprocess(self, input_image_size=None):
        """配置 AI2D 预处理管线 (letterbox pad + resize)。"""
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = (
                input_image_size if input_image_size
                else self.rgb888p_size
            )
            top, bottom, left, right, _ = letterbox_pad_param(
                self.rgb888p_size, self.model_input_size
            )
            # pad 填充色 = ImageNet 均值 [104, 117, 123]
            self.ai2d.pad(
                [0, 0, 0, 0, top, bottom, left, right], 0,
                [104, 117, 123]
            )
            self.ai2d.resize(
                nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel
            )
            self.ai2d.build(
                [1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                [1, 3, self.model_input_size[1], self.model_input_size[0]]
            )

    def postprocess(self, results):
        """后处理：调用 aidemo 的 face_det_post_process。"""
        with ScopedTiming("postprocess", self.debug_mode > 0):
            post_ret = aidemo.face_det_post_process(
                self.confidence_threshold,
                self.nms_threshold,
                self.model_input_size[1],
                self.anchors,
                self.rgb888p_size,
                results
            )
            if len(post_ret) == 0:
                return []
            return post_ret[0]

    def draw_result(self, pl, dets):
        """在 OSD 层绘制检测框。"""
        with ScopedTiming("display_draw", self.debug_mode > 0):
            if dets:
                pl.osd_img.clear()
                for det in dets:
                    x, y, w, h = map(
                        lambda v: int(round(v, 0)), det[:4]
                    )
                    # 坐标缩放：rgb888p → display
                    x = x * self.display_size[0] // self.rgb888p_size[0]
                    y = y * self.display_size[1] // self.rgb888p_size[1]
                    w = w * self.display_size[0] // self.rgb888p_size[0]
                    h = h * self.display_size[1] // self.rgb888p_size[1]
                    pl.osd_img.draw_rectangle(
                        x, y, w, h,
                        color=(255, 255, 0, 255), thickness=2
                    )
            else:
                pl.osd_img.clear()

    def draw_on_image(self, img, dets):
        """直接在 image.Image 上绘制检测框（不依赖 PipeLine）。"""
        if not dets:
            return
        sc_x = self.display_size[0] // self.rgb888p_size[0]
        sc_y = self.display_size[1] // self.rgb888p_size[1]
        for det in dets:
            x, y, w, h = map(lambda v: int(round(v, 0)), det[:4])
            x = x * sc_x
            y = y * sc_y
            w = w * sc_x
            h = h * sc_y
            img.draw_rectangle(x, y, w, h, color=(255, 255, 0), thickness=2)
