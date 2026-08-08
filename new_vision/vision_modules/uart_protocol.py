"""
uart_protocol.py — UART 协议: 钢球检测 → 小车主控 (ASCII 帧 + 校验)

帧格式: $B,n,x,y,w,h,dx,dy,dist_mm,flags[,...]*CS\r\n
协议详情见 k230-steelball-vision/UART协议说明.md
"""


def checksum(body):
    """'$'与'*'之间所有字符逐字节累加 mod 256，返回两位大写 hex"""
    s = 0
    for ch in body:
        s = (s + ord(ch)) & 0xFF
    return "%02X" % s


def pack_frame(targets):
    """targets: [(x,y,w,h,dx,dy,dist_mm,flags), ...] → 完整 ASCII 帧"""
    body = "B,%d" % len(targets)
    for t in targets:
        body += ",%d,%d,%d,%d,%d,%d,%d,%d" % t
    return "$%s*%s\r\n" % (body, checksum(body))


def calc_flags(x, y, w, h, dist_cm,
               disp_w=640, disp_h=480, edge_margin=2,
               k_dist=0.0, dist_min_cm=5.0, dist_max_cm=150.0):
    """→ (flags, dist_mm)。flags: bit0=valid, bit1=edge, bit2=range"""
    if dist_cm <= 0:
        dist_mm = 0
    else:
        dist_mm = int(dist_cm * 10 + 0.5)
        if dist_mm > 9999:
            dist_mm = 9999
    edge = (x <= edge_margin or y <= edge_margin or
            x + w >= disp_w - edge_margin or
            y + h >= disp_h - edge_margin)
    in_range = (k_dist > 0 and dist_min_cm <= dist_cm <= dist_max_cm)
    valid = (w > 0 and h > 0 and in_range and not edge)
    flags = (1 if valid else 0) | (2 if edge else 0) | (0 if in_range else 4)
    return flags, dist_mm
