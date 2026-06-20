#!/usr/bin/env python3
"""
decode_shape.py — X68000 Ultima IV tileset (SWSHAPE.PAT / shape.pat) 解碼器。

輸入 read_hdm.py 抽出的 SWSHAPE.PAT(Britannia disk,62464 bytes)或
shape.pat(Program disk,212544 bytes),解成可檢視的 PNG 接觸表(sprite sheet)。

格式現況(recon 已確認 / 仍待 pixel-perfect 校正)
-------------------------------------------------
已確認:
  * 無壓縮(gzip 再壓比 ≈1.0;對照 .LWZ 的 Amiga 版才是 LZW 壓縮)。
  * **SWSHAPE.PAT = 16×16 2bpp(4 色),非 4bpp**。byte 自相關 lag=4(+8/12/16/…)
    = 4 byte/row;16 寬 ÷ 4 byte = 2bpp;62464 ÷ 64 = 976 tiles。以 `twobpp` 模式
    解出**乾淨可辨識 sprite**(人形/劍/箭,無倍增)。原先 chunky4(8 byte/row)
    把 2 個真實 row 擠成 1 row → 才出現「8px 成對+水平錯位」的假象,已排除。
  * tile 基本尺寸 16×16(U4 標準 tile)。

TODO(尚未定到 pixel-perfect):
  * **palette 未定**:2bpp 每 tile 只用 4 色,X68000 透過 GVRAM palette 暫存器選
    子盤。完整 16 色 palette 在 ult4.x / init.x 初始化碼(16-bit word GRB 5-5-5)
    或某 .PAT/.DAT;掃描有多個候選(0x3c/0x3e/0x46…),需逐一套已知 tile 比對 pin。
  * **哪個檔是 256 地圖 tile + tile 序**:SWSHAPE 頭幾個 tile 是人形非水/草地形,
    需找 tile 0=水 的對齊點;`shape.pat`(212544)autocorr lag=18 結構不同(疑 portrait/
    大圖),非地圖 tile。對齊 xu4 256-tile 序待定。
  * 目前用灰階占位 palette,可用 --palette 餵 16*3 RGB 表。

用法
----
    python3 decode_shape.py <SWSHAPE.PAT> -o sheet.png
    python3 decode_shape.py <shape.pat>  -o sheet.png --mode planar --tile 16x16
    python3 decode_shape.py <SWSHAPE.PAT> -o sheet.png --palette pal.bin   # 16*3 bytes RGB

走 docker u4cht/extract(python3 + Pillow)。
"""
import argparse

from PIL import Image

# 占位灰階 palette(16 色);bg(0)用深藍以便看出 tile 邊界。真實 palette 待抽。
DEFAULT_PALETTE = [(0, 0, 80)] + [
    (16 * i, 16 * i, 16 * i) for i in range(1, 16)
]


def load_palette(path):
    """讀 16*3 = 48 bytes 的 RGB palette;不足則退回預設。"""
    if not path:
        return DEFAULT_PALETTE
    raw = open(path, "rb").read()
    if len(raw) < 48:
        return DEFAULT_PALETTE
    return [(raw[i * 3], raw[i * 3 + 1], raw[i * 3 + 2]) for i in range(16)]


def decode_tile_chunky4(data, off, tw, th, pal):
    """chunky 4bpp:2 px/byte,row-major,(tw//2) byte/row。已驗證可 dump 字形。"""
    img = Image.new("RGB", (tw, th))
    px = img.load()
    row_bytes = tw // 2
    for y in range(th):
        for x in range(tw):
            bi = off + y * row_bytes + x // 2
            if bi >= len(data):
                continue
            b = data[bi]
            v = (b >> 4) if (x % 2 == 0) else (b & 0x0F)
            px[x, y] = pal[v]
    return img


def decode_tile_planar(data, off, tw, th, pal):
    """planar 4bpp:4 個 bitplane 連續存放,每 plane (tw//8)*th bytes。

    TODO: plane 排列(連續 vs word-interleaved)與 bit 順序待從繪圖常式反組譯確認;
    這裡先用「連續 plane、MSB-first」最常見假設。
    """
    img = Image.new("RGB", (tw, th))
    px = img.load()
    plane_bytes = (tw // 8) * th
    for y in range(th):
        for x in range(tw):
            v = 0
            for p in range(4):
                po = off + p * plane_bytes + y * (tw // 8) + x // 8
                if po >= len(data):
                    bit = 0
                else:
                    bit = (data[po] >> (7 - (x % 8))) & 1
                v |= bit << p
            px[x, y] = pal[v]
    return img


def decode_tile_2bpp(data, off, tw, th, pal):
    """2bpp(4 色):4 px/byte,row-major,(tw//4) byte/row,(tw*th//4) byte/tile。

    **這是 SWSHAPE.PAT 的正確格式**(byte 自相關 lag=4 = 4 byte/row;16 寬 → 2bpp;
    62464/64 = 976 tiles)。agent 原以 chunky4(8 byte/row)解才出現「8px 成對+錯位」
    —— 那是把 2 個真實 row 擠進 1 row + nibble 誤判。pal 只用前 4 色(idx 0-3)。
    """
    img = Image.new("RGB", (tw, th))
    px = img.load()
    row_bytes = tw // 4
    for y in range(th):
        for x in range(tw):
            bi = off + y * row_bytes + x // 4
            if bi >= len(data):
                continue
            b = data[bi]
            shift = (3 - (x % 4)) * 2            # MSB-first,2 bit/px
            px[x, y] = pal[(b >> shift) & 3]
    return img


DECODERS = {"twobpp": decode_tile_2bpp,
            "chunky4": decode_tile_chunky4, "planar": decode_tile_planar}
BYTES_PER_TILE = {"twobpp": 4, "chunky4": 2, "planar": 2}  # 分母:px→byte


def parse_tile(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shape", help="SWSHAPE.PAT 或 shape.pat")
    ap.add_argument("-o", "--out", default="shape_sheet.png", help="輸出 PNG")
    ap.add_argument("--mode", choices=DECODERS, default="twobpp",
                    help="解碼模式(預設 twobpp = SWSHAPE 正確格式;chunky4/planar 為對照)")
    ap.add_argument("--tile", default="16x16", help="tile 尺寸 WxH(預設 16x16)")
    ap.add_argument("--cols", type=int, default=16, help="接觸表每列 tile 數")
    ap.add_argument("--scale", type=int, default=3, help="輸出 nearest 放大倍率")
    ap.add_argument("--palette", help="16*3 bytes RGB palette(省略用灰階占位)")
    args = ap.parse_args()

    data = open(args.shape, "rb").read()
    tw, th = parse_tile(args.tile)
    bpt = (tw * th) // BYTES_PER_TILE[args.mode]   # 2bpp=tile/4、4bpp=tile/2
    pal = load_palette(args.palette)
    decode = DECODERS[args.mode]

    ntile = len(data) // bpt
    rows = (ntile + args.cols - 1) // args.cols
    sheet = Image.new("RGB",
                      (args.cols * (tw + 2), rows * (th + 2)), (30, 30, 30))
    for i in range(ntile):
        tile = decode(data, i * bpt, tw, th, pal)
        ox = (i % args.cols) * (tw + 2) + 1
        oy = (i // args.cols) * (th + 2) + 1
        sheet.paste(tile, (ox, oy))

    if args.scale > 1:
        sheet = sheet.resize((sheet.width * args.scale, sheet.height * args.scale),
                             Image.NEAREST)
    sheet.save(args.out)
    print(f"# {args.shape}: {len(data)} bytes, {ntile} tiles "
          f"({tw}x{th}, {args.mode}) -> {args.out}")


if __name__ == "__main__":
    main()
