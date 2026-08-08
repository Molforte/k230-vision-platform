"""
K230 → MSPM0G3507 持续通信 (K230 端)
=====================================
接线:
  K230 IO32 (UART3_TXD)  →  MSP PA11 (UART0_RX)
  K230 IO33 (UART3_RXD)  →  MSP PA10 (UART0_TX)
  K230 GND               →  MSP GND

每 0.5s 发送一次消息，MSP 收到后回传并亮 LED。
"""

import sys
sys.path.insert(0, "/sdcard")

from vision_modules.uart_link import UartLink
import time

# ============================================================
# 初始化
# ============================================================
print("=" * 48)
print("  K230 <-> MSPM0G3507 持续通信")
print("=" * 48)

try:
    link = UartLink(baudrate=115200)
    print("  UART 初始化成功")
except Exception as e:
    print(f"  初始化失败: {e}")
    sys.exit(1)

# 连通性探测
ok, rx = link.send_and_verify(b"\xAA", timeout_ms=1000)
if not ok:
    print("  MSP 无响应，请检查接线/烧录")
    link.deinit()
    sys.exit(1)
print("  MSP Echo Server 在线\n")

# ============================================================
# 持续发送
# ============================================================
seq = 0
msg = "Hello MSP {}"

print("开始持续通信 (0.5s/次)，Ctrl+C 停止\n")

try:
    while True:
        seq += 1
        payload = msg.format(seq).encode()
        link.flush()
        link.write(payload)

        # 等待 MSP 回传
        rx = link.timed_read(len(payload), timeout_ms=300)

        if rx == payload:
            print("[#{:04d}] OK  '{}'".format(seq, rx.decode()))
        elif rx:
            print("[#{:04d}] ??  sent:'{}'  got:'{}'".format(
                seq, payload.decode(), rx.decode(errors="replace")))
        else:
            print("[#{:04d}] TIMEOUT".format(seq))

        time.sleep_ms(500)

except KeyboardInterrupt:
    print("\n\n用户停止")

link.deinit()
print("=" * 48)
