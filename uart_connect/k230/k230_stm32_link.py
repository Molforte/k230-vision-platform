"""
K230 <-> STM32 UART 联调测试 (K230 端)
=======================================
接线:
  K230 IO32 (UART3_TX)  →  STM32 PA3  (USART2_RX)
  K230 IO33 (UART3_RX)  →  STM32 PA2  (USART2_TX)
  K230 GND              →  STM32 GND

测试: K230 发送 → STM32 回传 → K230 校验
"""

from machine import UART, FPIOA
import time

# ============================================================
# 初始化 UART3
# ============================================================
fpioa = FPIOA()
fpioa.set_function(32, FPIOA.UART3_TXD)
fpioa.set_function(33, FPIOA.UART3_RXD)

uart = UART(
    UART.UART3,
    baudrate=115200,
    bits=UART.EIGHTBITS,
    parity=UART.PARITY_NONE,
    stop=UART.STOPBITS_ONE,
)

def flush():
    while uart.any():
        uart.read()

def send_and_verify(payload, timeout_ms=500):
    """发送数据并等待相同长度的回传，返回 (True/False, 回传数据)。"""
    flush()
    uart.write(payload)

    deadline = time.ticks_ms() + timeout_ms
    buf = bytearray()
    while len(buf) < len(payload):
        need = len(payload) - len(buf)
        chunk = uart.read(need)
        if chunk:
            buf += chunk
        elif time.ticks_diff(time.ticks_ms(), deadline) > 0:
            break

    rx = bytes(buf)
    ok = (rx == payload)
    return ok, rx

# ============================================================
# 测试
# ============================================================
print("=" * 48)
print("K230 <-> STM32 UART Link Test")
print("=" * 48)

passed = 0
failed = 0

# 1. 单字节遍历
print("\n[1] Single-byte sweep 0x00..0xFF")
errors = 0
for v in range(256):
    ok, rx = send_and_verify(bytes([v]))
    if not ok:
        errors += 1
        if errors <= 5:
            print(f"  FAIL: sent 0x{v:02X}, got {rx.hex() if rx else '(timeout)'}")
if errors == 0:
    print("  PASS (256/256)")
    passed += 1
else:
    print(f"  FAIL ({errors}/256)")
    failed += 1

# 2. 变长包
print("\n[2] Variable-length packets")
for n in [1, 4, 16, 64, 128]:
    payload = bytes(i & 0xFF for i in range(n))
    ok, rx = send_and_verify(payload, timeout_ms=3000)
    if ok:
        print(f"  len={n:>3}: PASS")
        passed += 1
    else:
        print(f"  len={n:>3}: FAIL — got {len(rx)} bytes, expected {n}")
        if len(rx) > 0:
            for i, (a, b) in enumerate(zip(payload, rx)):
                if a != b:
                    print(f"          first diff at byte[{i}]: sent 0x{a:02X} got 0x{b:02X}")
                    break
            if len(rx) < len(payload) and rx == payload[:len(rx)]:
                print(f"          prefix matches, missing last {len(payload)-len(rx)} bytes")
        failed += 1

# 3. 边界模式
print("\n[3] Edge patterns")
patterns = [
    ("all-0x00", bytes([0x00] * 64)),
    ("all-0xFF", bytes([0xFF] * 64)),
    ("0x55-alt", bytes([0x55] * 64)),
    ("0xAA-alt", bytes([0xAA] * 64)),
]
for name, payload in patterns:
    ok, _ = send_and_verify(payload)
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    if ok:
        passed += 1
    else:
        failed += 1

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 48)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 48)
