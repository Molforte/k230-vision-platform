"""
K230 Vision Module Library — 电赛视觉模块集

Usage:
    from vision import Camera, ColorTracker, ShapeDetector
    cam = Camera.init()
    ct = ColorTracker(thresholds=...)
    blobs = ct.detect(cam.snap())
"""

from vision.vision_utils import Camera, ColorPresets, measure_distance
from vision.color_tracker import ColorTracker
from vision.shape_detector import ShapeDetector
from vision.line_detector import LineDetector
from vision.face_detector import FaceDetector
from vision.motion_detector import MotionDetector
from vision.tag_reader import TagReader
