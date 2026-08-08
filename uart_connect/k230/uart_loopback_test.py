"""
K230 UART 自发自收 (Loopback) 验证脚本 — YahBoom 版
=====================================================
接线：用杜邦线将 IO32 (UART3_TXD) 和 IO33 (UART3_RXD) 短接。

测试内容：
  1. 连通性探测（发 0xAA，确认回环）
  2. 单字节遍历 0x00~0xFF
  3. 不同长度数据包（1, 4, 16, 64, 256 字节）
  4. 边界模式（全0、全1、交替、递增/递减）
  5. 三个波特率各跑一轮（9600, 115200, 1152000）
"""

from machine import UART, FPIOA
import time

# ============================================================
# 配置
# ============================================================
UART_ID   = UART.UART3       # UART3
TX_PIN    = 32               # IO32 → UART3_TXD
RX_PIN    = 33               # IO33 → UART3_RXD

BAUD_RATES     = [9600, 115200, 1152000]
READ_TIMEOUT_MS = 200

# ============================================================
# 初始化
# ============================================================

def init_uart():
    """配置 FPIOA 引脚映射并创建 UART3 实例。"""
    fpioa = FPIOA()

    # IO32 → UART3_TXD, IO33 → UART3_RXD
    fpioa.set_function(TX_PIN, FPIOA.UART3_TXD)
    fpioa.set_function(RX_PIN, FPIOA.UART3_RXD)

    # 先用默认 115200 初始化，后面每个波特率测试会用 init() 切换
    uart = UART(
        UART_ID,
        baudrate=115200,
        bits=UART.EIGHTBITS,
        parity=UART.PARITY_NONE,
        stop=UART.STOPBITS_ONE,
    )
    # 清空接收缓冲区
    uart.read()
    return uart


def flush_rx(uart):
    """清空接收缓冲区。"""
    while uart.any():
        uart.read()


def timed_read(uart, expected_len, timeout_ms=READ_TIMEOUT_MS):
    """等待并读取指定长度的数据，超时返回已读到的部分。"""
    deadline = time.ticks_ms() + timeout_ms
    buf = bytearray()
    while len(buf) < expected_len:
        if uart.any():
            chunk = uart.read()
            if chunk:
                buf += chunk
        if time.ticks_diff(time.ticks_ms(), deadline) > 0:
            break
    return bytes(buf)


# ============================================================
# 测试用例
# ============================================================

def test_probe(uart, baud):
    """连通性探测：发 0xAA，确认能收到。"""
    flush_rx(uart)
    uart.write(b"\xAA")
    rx = timed_read(uart, 1, timeout_ms=300)
    if rx and rx[0] == 0xAA:
        print("  连通性: PASS")
        return True
    else:
        print(f"  连通性: FAIL (sent 0xAA, got {rx.hex() if rx else 'timeout'})")
        return False


def test_single_byte(uart, baud):
    """单字节遍历 0x00~0xFF。"""
    errors = 0
    for val in range(256):
        flush_rx(uart)
        uart.write(bytes([val]))
        rx = timed_read(uart, 1, timeout_ms=100)
        if len(rx) != 1 or rx[0] != val:
            errors += 1
            if errors <= 5:
                print(f"  FAIL: sent 0x{val:02X}, got {rx.hex() if rx else '(timeout)'}")
    if errors == 0:
        print(f"  单字节遍历: PASS (256/256)")
    else:
        print(f"  单字节遍历: FAIL ({errors}/256 errors)")
    return errors == 0


def test_variable_length(uart, baud):
    """不同长度数据包。"""
    all_pass = True
    for length in [1, 4, 16, 64, 256]:
        payload = bytes(i & 0xFF for i in range(length))
        flush_rx(uart)
        uart.write(payload)
        rx = timed_read(uart, length)
        if rx != payload:
            if len(rx) != length:
                print(f"  FAIL: len={length}, only got {len(rx)} bytes")
            else:
                for i, (s, r) in enumerate(zip(payload, rx)):
                    if s != r:
                        print(f"  FAIL: len={length}, byte[{i}] 0x{s:02X}→0x{r:02X}")
                        break
            all_pass = False
    if all_pass:
        print(f"  变长包: PASS (1/4/16/64/256)")
    return all_pass


def test_edge_patterns(uart, baud):
    """边界模式。"""
    patterns = [
        ("全 0x00",   bytes([0x00] * 64)),
        ("全 0xFF",   bytes([0xFF] * 64)),
        ("0x55 交替", bytes([0x55] * 64)),
        ("0xAA 交替", bytes([0xAA] * 64)),
        ("递增 0..63", bytes(range(64))),
        ("递减 63..0", bytes(range(63, -1, -1))),
    ]
    all_pass = True
    for name, payload in patterns:
        flush_rx(uart)
        uart.write(payload)
        rx = timed_read(uart, len(payload))
        if rx != payload:
            print(f"  FAIL: [{name}]")
            all_pass = False
    if all_pass:
        print(f"  边界模式: PASS (6 patterns)")
    return all_pass


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 56)
    print("  K230 UART Loopback Test — YahBoom")
    print("=" * 56)
    print(f"  UART  : UART3")
    print(f"  TX    : IO{TX_PIN}")
    print(f"  RX    : IO{RX_PIN}")
    print(f"  接线  : 杜邦线短接 IO{TX_PIN} 和 IO{RX_PIN}")
    print("=" * 56)

    # 初始化 UART（FPIOA 映射一次即可）
    try:
        uart = init_uart()
        print("UART3 + FPIOA 初始化成功\n")
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    results = {}

    for baud in BAUD_RATES:
        print(f">>> 波特率: {baud} <<<")
        # 用 init() 切换波特率，不需要重新创建对象
        uart.init(baudrate=baud)
        time.sleep_ms(50)

        # 连通性探测
        if not test_probe(uart, baud):
            print("  ** 无回环数据，请检查 IO32↔IO33 杜邦线！ **")
            print("  ** 如接线正确仍失败，UART3 可能被大核占用。 **")
            results[baud] = False
            continue

        p1 = test_single_byte(uart, baud)
        p2 = test_variable_length(uart, baud)
        p3 = test_edge_patterns(uart, baud)
        results[baud] = p1 and p2 and p3

    uart.deinit()

    # 汇总
    print("\n" + "=" * 56)
    print("  测试汇总")
    print("=" * 56)
    for baud, passed in results.items():
        print(f"  {baud:>8} baud  →  {'PASS' if passed else 'FAIL'}")

    if all(results.values()):
        print("\n  OK — UART3 自发自收全部通过。")
    else:
        failed = [b for b, p in results.items() if not p]
        print(f"\n  失败波特率: {failed}")
        print("  排查建议:")
        print("    1. 确认 IO32、IO33 杜邦线连接牢固")
        print("    2. 确认引脚未被其他外设复用")
        print("    3. UART3 如被大核占用，换 UART2 (IO5/IO6) 试试")
    print("=" * 56)


if __name__ == "__main__":
    main()
