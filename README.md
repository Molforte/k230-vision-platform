# 2026 年电子设计竞赛 · K230 常用视觉模块

[![CI](https://github.com/Molforte/k230-vision-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Molforte/k230-vision-platform/actions/workflows/ci.yml)

本项目收录了一些我在电赛筹备期间写完的一些基础的视觉模块，所有的项目文件均有做过优化与调试，搭载型号主要为YahBoom的 K230，其他平台/型号未知。

---
## 硬件

| 组件  | 型号                         | 用途                         |
| --- | -------------------------- | -------------------------- |
| 主控  | YahBoom CanMV K230         | MicroPython v1.8, 视觉推理     |
| 摄像头 | GC2093 (CSI)               | 1920×1080@60 / 1280×960@90 |
| 显示屏 | ST7701 LCD                 | 640×480 实时叠加               |
| 下位机 | STM32F103C8T6 / MSPM0G3507 | 电机/舵机控制                    |
| 通信  | UART 115200-8N1            | K230→下位机 数据帧               |

---
## 目录结构

```
├── k230_vision/                     # K230 视觉代码
│   ├── main_steel_ball_detect.py    # 钢珠检测 + 跟踪 + 测距 + UART
│   ├── main_face_detect.py          # 人脸检测 (anchor-based, 320×320)
│   ├── main_line_detect.py          # 巡线 (灰度 ROI)
│   ├── main_color_shape_detect.py   # 颜色+形状联合检测
│   ├── main_color_detect.py         # 颜色追踪
│   ├── main_shape_detect.py         # 形状检测
│   ├── main_uart_msp_link.py        # K230↔MSP 通信测试
│   ├── vision_modules/              # 可复用视觉模块
│   │   ├── steel_ball_tracker.py    #   多目标跟踪器 (最近邻+滑动平均)
│   │   ├── uart_protocol.py         #   UART ASCII 帧协议
│   │   ├── face_detector.py         #   人脸检测器
│   │   ├── line_detector.py         #   巡线检测器
│   │   ├── color_shape_detector.py  #   颜色形状检测器
│   │   ├── color_tracker.py         #   颜色追踪器
│   │   ├── shape_detector.py        #   形状检测器
│   │   └── camera_utils.py          #   摄像头/显示器初始化
│   └── face_detection_320.kmodel    # 人脸检测模型
├── stm32_uart/                      # STM32 下位机固件 (CubeIDE)
│   ├── stm32f103c8t6_uart.ioc       #   CubeMX 工程
│   ├── Core/Src/main.c              #   缓冲式 Echo Server
│   └── CMakeLists.txt
├── uart_bridge/                     # K230↔STM32 通信方案
│   ├── k230_stm32_link.py           #   K230 端联调脚本
│   └── protocol.md                  #   通信协议说明
└── assets/                          # 接线图、演示照片
```

---
## 致谢

- 钢珠检测移植自 [k230-steelball-vision](https://github.com/Roast-2007/k230-steelball-vision)
- CanMV K230 固件: 01Studio
- YOLO11n 模型: 01Studio 在线训练平台

---
