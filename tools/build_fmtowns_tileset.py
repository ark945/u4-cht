#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 FM Towns 版 Ultima IV 的 shapes 圖建成 xu4 可用的 tileset PNG(16×4096)。

來源:materals/fmtowns/mshapes4.png —— FM Towns U4 的 256-tile shapes,排成
16×16 格、每格 64×64(原 16×16 的 4 倍 nearest 放大),canonical U4 256-tile 順序。
本腳本逐格抽出、降採樣回 16×16、依序堆成 16 寬 × 4096 高的垂直條(xu4 `tiles: 256`)。

> 為何不直接解 ULTIMA4.TIL:該 TIL 為 256 個連續 16×16 tile 的 16-bit 直色,但實測
> 其 16-bit 像素格式非標準 RGB565/555(LE/BE/BGR 各變體解出的水都偏紫、人物顏色錯),
> 確切位元佈局未解開;mshapes4.png 是已正確還原的同資料,直接採用。TIL 解碼待日後補。

FM Towns shapes 屬版權遊戲資料,不入 repo(引擎/資料分離);輸出留本機。

用法:
  python3 tools/build_fmtowns_tileset.py --msh <mshapes4.png> --out fmt_tileset.png
"""
import argparse
from PIL import Image

N_TILES = 256
COLS = 16        # mshapes4 每列 16 格


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--msh", required=True, help="FM Towns mshapes4.png(16×16 格)")
    ap.add_argument("--out", required=True, help="輸出 tileset PNG(16×4096)")
    args = ap.parse_args()

    m = Image.open(args.msh).convert("RGB")
    W, H = m.size
    ts = W // COLS                      # 來源每格邊長(mshapes4 = 64)
    if ts < 16 or W % COLS:
        raise SystemExit(f"mshapes4 尺寸異常:{W}×{H}(每列 {COLS} 格無法整除)")

    out = Image.new("RGB", (16, 16 * N_TILES))
    po = out.load()
    for idx in range(N_TILES):
        gr, gc = idx // COLS, idx % COLS
        tile = m.crop((gc * ts, gr * ts, gc * ts + ts, gr * ts + ts)) \
                .resize((16, 16), Image.NEAREST)
        tp = tile.load()
        for y in range(16):
            for x in range(16):
                po[x, idx * 16 + y] = tp[x, y]
    out.save(args.out)
    print(f"FM Towns tileset:{N_TILES} tile → {args.out} (16×{16*N_TILES})")


if __name__ == "__main__":
    main()
