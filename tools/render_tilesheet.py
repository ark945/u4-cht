#!/usr/bin/env python3
"""把 U4 SHAPES.EGA / shapes.vga 解碼成 16×16-tile 的 tile sheet PNG(README 展示用)。
EGA:256 tile,每 tile 16×16、4bpp(2 px/byte,高 nibble=左),標準 EGA 16 色。
VGA:256 tile,每 tile 16×16、8bpp,u4vga.pal(256×3,VGA 6-bit)。
"""
import sys, struct
from PIL import Image

EGA = [(0,0,0),(0,0,170),(0,170,0),(0,170,170),(170,0,0),(170,0,170),
       (170,85,0),(170,170,170),(85,85,85),(85,85,255),(85,255,85),
       (85,255,255),(255,85,85),(255,85,255),(255,255,85),(255,255,255)]

def load_vga_pal(path):
    d = open(path,'rb').read()
    return [((d[i*3]*255)//63,(d[i*3+1]*255)//63,(d[i*3+2]*255)//63) for i in range(256)]

def decode_ega(path, ntiles=256, tw=16, th=16):
    d = open(path,'rb').read()
    tiles=[]
    bpt = tw*th//2   # 128
    for t in range(ntiles):
        img = Image.new('RGB',(tw,th))
        px = img.load()
        base = t*bpt
        for i in range(tw*th):
            b = d[base + i//2]
            nib = (b>>4) if (i%2==0) else (b&0xF)
            px[i%tw, i//tw] = EGA[nib]
        tiles.append(img)
    return tiles

def decode_vga(path, pal, ntiles=256, tw=16, th=16):
    d = open(path,'rb').read()
    tiles=[]
    bpt = tw*th   # 256
    for t in range(ntiles):
        img = Image.new('RGB',(tw,th))
        px = img.load()
        base = t*bpt
        for i in range(tw*th):
            px[i%tw, i//tw] = pal[d[base+i]]
        tiles.append(img)
    return tiles

def sheet(tiles, cols=16, scale=3, pad=1, bg=(32,32,40)):
    tw,th = tiles[0].size
    rows = (len(tiles)+cols-1)//cols
    W = cols*(tw*scale+pad)+pad
    H = rows*(th*scale+pad)+pad
    out = Image.new('RGB',(W,H),bg)
    for idx,t in enumerate(tiles):
        ts = t.resize((tw*scale,th*scale),Image.NEAREST)
        c,r = idx%cols, idx//cols
        out.paste(ts,(pad+c*(tw*scale+pad), pad+r*(th*scale+pad)))
    return out

if __name__=='__main__':
    mode, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv)>4 else 256
    if mode=='ega':
        tiles = decode_ega(src, n)
    else:
        pal = load_vga_pal(sys.argv[5])
        tiles = decode_vga(src, pal, n)
    sheet(tiles[:n]).save(out)
    print(f"wrote {out} ({n} tiles)")
