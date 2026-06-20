#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SMS(Sega Master System)tile 解碼/掃描。
tile = 8×8 4bpp planar:每 row 4 byte(plane0..3,weight 1/2/4/8),MSB=左。32B/tile。
模式:
  overview <rom> <out>            整顆 ROM 當 8×8 tile strip(灰階)找圖形區
  page <rom> <out> <off> <ntile>  從 off 起 n 個 tile 放大彩色(找 U4 tile)
"""
import sys
from PIL import Image

mode = sys.argv[1]
rom = open(sys.argv[2], "rb").read()
out = sys.argv[3]

# 16 級灰階
GRAY = [(i * 17, i * 17, i * 17) for i in range(16)]
# 暫用對比色盤(找圖用)
PAL = [
    (0, 0, 0), (60, 60, 60), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (181, 82, 77), (102, 235, 250),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]


def decode_tile(tb):
    """32 byte → 64 index(8×8 row-major)。"""
    px = [0] * 64
    for row in range(8):
        b = [tb[row * 4 + p] for p in range(4)]
        for x in range(8):
            v = 0
            for p in range(4):
                if (b[p] >> (7 - x)) & 1:
                    v |= (1 << p)
            px[row * 8 + x] = v
    return px


if mode == "overview":
    NT = len(rom) // 32
    COLS = 64
    ROWS = (NT + COLS - 1) // COLS
    img = Image.new("RGB", (COLS * 8, ROWS * 8))
    p = img.load()
    for t in range(NT):
        tb = rom[t * 32:t * 32 + 32]
        if len(tb) < 32:
            break
        px = decode_tile(tb)
        ox, oy = (t % COLS) * 8, (t // COLS) * 8
        for i, v in enumerate(px):
            p[ox + i % 8, oy + i // 8] = GRAY[v]
    img.save(out)
    print(f"overview: {NT} tiles, {COLS}×{ROWS}, img {img.size}")

elif mode == "page":
    off = int(sys.argv[4], 0)
    ntile = int(sys.argv[5])
    COLS = 16
    ROWS = (ntile + COLS - 1) // COLS
    SC = 6
    img = Image.new("RGB", (COLS * 8 * SC, ROWS * 8 * SC), (80, 0, 80))
    p = img.load()
    for t in range(ntile):
        tb = rom[off + t * 32:off + t * 32 + 32]
        if len(tb) < 32:
            break
        px = decode_tile(tb)
        ox, oy = (t % COLS) * 8 * SC, (t // COLS) * 8 * SC
        for i, v in enumerate(px):
            col = PAL[v]
            for dy in range(SC):
                for dx in range(SC):
                    p[ox + (i % 8) * SC + dx, oy + (i // 8) * SC + dy] = col
    img.save(out)
    print(f"page @0x{off:X}: {ntile} tiles -> {out}")
