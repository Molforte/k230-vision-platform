"""
uart_link.py — K230 UART 通信模块 (MSPM0G3507)
===============================================
提供 UART 初始化、发送、接收、校验等基础操作，
可供 main 脚本或 vision 模块直接复用。

接线:
  K230 IO32 (UART3_TXD)  →  MSP PA11 (UART0_RX)
  K230 IO33 (UART3_RXD)  →  MSP PA10 (UART0_TX)
  K230 GND               →  MSP GND
"""

from machine import UART, FPIOA
import time


class UartLink:
    """K230 UART 通信链路，封装 MicroPython UART 操作。"""

    def __init__(self,
                 uart_id=UART.UART3,
                 tx_pin=32,
                 rx_pin=33,
                 baudrate=115200,
                 bits=UART.EIGHTBITS,
                 parity=UART.PARITY_NONE,
                 stop=UART.STOPBITS_ONE):
        self.uart_id = uart_id
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baudrate = baudrate

        # FPIOA 引脚映射
        fpioa = FPIOA()
        try:
            fpioa.set_function(tx_pin, FPIOA.UART3_TXD)
            fpioa.set_function(rx_pin, FPIOA.UART3_RXD)
        except Exception:
            # 如果 UART3 被占用，尝试 UART2
            fpioa.set_function(tx_pin, FPIOA.UART2_TXD)
            fpioa.set_function(rx_pin, FPIOA.UART2_RXD)
            self.uart_id = UART.UART2

        self._uart = UART(self.uart_id,
                          baudrate=baudrate,
                          bits=bits,
                          parity=parity,
                          stop=stop)
        # 清空上电残留
        self.flush()

    # ── 基础操作 ──────────────────────────────────────────

    def flush(self):
        """清空接收缓冲区。"""
        while self._uart.any():
            self._uart.read()

    def write(self, data):
        """发送原始字节。"""
        return self._uart.write(data)

    def read(self, n=None):
        """读取 n 字节（None = 读取当前缓冲区全部）。"""
        if n is None:
            return self._uart.read() or b""
        return self._uart.read(n) or b""

    def any(self):
        """返回可读字节数。"""
        return self._uart.any()

    def deinit(self):
        """释放 UART 资源。"""
        if self._uart:
            self._uart.deinit()

    # ── 高级操作 ──────────────────────────────────────────

    def timed_read(self, expected_len, timeout_ms=500):
        """等待并读取指定长度的数据，超时返回已读到的部分。"""
        deadline = time.ticks_ms() + timeout_ms
        buf = bytearray()
        while len(buf) < expected_len:
            chunk = self.read()
            if chunk:
                buf += chunk
            if time.ticks_diff(time.ticks_ms(), deadline) > 0:
                break
        return bytes(buf)

    def send_and_verify(self, payload, timeout_ms=500):
        """发送数据并等待相同长度的回传，返回 (ok, rx_data)。"""
        self.flush()
        self.write(payload)
        rx = self.timed_read(len(payload), timeout_ms)
        return rx == payload, rx

    def recv_until_idle(self, timeout_ms=500, idle_ms=20):
        """接收数据直到线路空闲 idle_ms 毫秒，返回完整数据。"""
        deadline = time.ticks_ms() + timeout_ms
        buf = bytearray()
        last_rx = time.ticks_ms()
        while True:
            chunk = self.read()
            if chunk:
                buf += chunk
                last_rx = time.ticks_ms()
            now = time.ticks_ms()
            if time.ticks_diff(now, deadline) > 0:
                break
            if len(buf) > 0 and time.ticks_diff(now, last_rx) >= idle_ms:
                break
        return bytes(buf)
