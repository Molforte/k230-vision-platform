# K230 ↔ STM32 UART 联调 — 项目存档

## 项目目标
为电子设计竞赛打通 K230 (视觉) 与 STM32F103C8T6 之间的 UART 通信链路。

## 硬件

| 设备 | 型号 | 备注 |
|---|---|---|
| K230 | YahBoom CanMV K230 | MicroPython 固件 v1.8 |
| STM32 | STM32F103C8T6 最小系统板 | HAL 库, CubeMX 6.17, GCC |

## UART 配置

| 板子 | 串口 | TX | RX | 波特率 | 用途 |
|---|---|---|---|---|---|
| K230 | UART3 | IO32 | IO33 | 115200-8N1 | 与 STM32 通信 |
| STM32 | USART1 | PA9 | PA10 | 115200-8N1 | printf 调试输出 (需 USB-TTL) |
| STM32 | USART2 | PA2 | PA3 | 115200-8N1 | 与 K230 通信 (Echo Server) |

## 联调接线

```
K230 IO32  ──→  STM32 PA3   (TX → RX)
K230 IO33  ──→  STM32 PA2   (RX → TX)
K230 GND   ──→  STM32 GND
```

## 文件说明

### k230/
- **uart_loopback_test.py** — K230 UART3 自发自收验证 (IO32↔IO33 杜邦线短接, 多波特率)
- **k230_stm32_link.py** — K230↔STM32 联调测试：发送→等待回传→校验

### stm32f103c8t6_uart/ (完整 CubeIDE 项目)
开箱即用：双击 `stm32f103c8t6_uart.ioc` 在 CubeMX 中打开，CubeIDE 直接编译烧录。
- **Core/Src/main.c** — 缓冲式 Echo Server (USART2 收→缓冲 5ms→一次性回传)
- **Core/Src/stm32f1xx_hal_msp.c** — USART1+USART2 GPIO 初始化
- **build/** — 编译产物 (含 .elf, 可直接烧录)

## 关键技术决策

1. **USART2 用于跨板通信**：USART1 (PA9/PA10) 连着板载 CH340 芯片，做 loopback 时 CH340 的 TXD 输出与 STM32 TX 打架导致死循环。USART2 (PA2/PA3) 无冲突。

2. **缓冲式 Echo**：STM32 先收集完整一包数据（等 5ms 静默判结束），再一次性回传。避免逐字节 echo 时 K230 RX 缓冲区溢出（128 字节连续包会丢 7~8 字节）。

3. **STM32 端不用 HAL_MAX_DELAY**：在杂牌 STM32F103 板子上 HAL_MAX_DELAY 超时会导致 HAL_UART_Transmit/Receive 死循环。所有调用改用有限超时 (2000~5000ms)。

4. **K230 端发完立刻读**：uart.write() 后不加 sleep——echo 数据在发送期间已涌入 RX FIFO，sleep 会导致溢出丢字节。

## 验证状态
- [x] K230 UART3 自发自收 (9600/115200/1152000 全通过)
- [x] STM32 USART2 自发自收 (PA2↔PA3 杜邦线短接, PC13 LED 4 闪)
- [x] K230 ↔ STM32 联调 (10/10 全通过: 单字节 256 项, 变长包 5 项, 边界 4 项)

## 恢复步骤
1. STM32: 用 CubeIDE 打开 `stm32f103c8t6_uart/` 项目，编译烧录。上电后 PC13 LED 快闪 3 次 = 就绪。
2. K230: 运行 `k230/k230_stm32_link.py` 验证链路 (10/10 PASS)。
3. K230 自发自收: 运行 `k230/uart_loopback_test.py` (需 IO32↔IO33 短接)。
