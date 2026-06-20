#!/usr/bin/env python3
"""從 ult.mgd 抽 voice N(FM patch)→ 產 YM2151 register event(在 ch0 設音色 + 播音階)。
voice 結構(42B stride,起點 0x09):index + DT/MUL[4] + TL[4] + AR[4] + D1R[4] + D2R[4] + D1L-RR[4] + CON/FB + slot。
operator 順序先試 M1,M2,C1,C2(slot 0/8/16/24)。"""
import sys
d=open(sys.argv[1],"rb").read()
vn=int(sys.argv[2])  # voice 編號(1-based)
base=0x09+(vn-1)*0x2a
idx=d[base]
p=d[base+1:base+1+24]  # 6 param × 4 op
confb=d[base+25]
dtmul,tl,ar,d1r,d2r,d1lrr=[p[i*4:i*4+4] for i in range(6)]
SLOT=[0,8,16,24]  # M1,M2,C1,C2
ev=[]
def w(a,v): ev.append((a,v))
w(0x20, 0xC0|(confb&0x3f))  # RL=both + FB/CON
for op in range(4):
    s=SLOT[op]
    w(0x40+s, dtmul[op]&0x7f)
    w(0x60+s, tl[op]&0x7f)
    w(0x80+s, ar[op]&0x1f)      # KS=0
    w(0xA0+s, d1r[op]&0x9f)
    w(0xC0+s, d2r[op]&0x9f)
    w(0xE0+s, d1lrr[op])
# 播音階:幾個 KC
import sys
out=open(sys.argv[3],"w")
for a,v in ev: out.write(f"{a:02x} {v:02x} 0\n")
scale=[0x4a,0x4d,0x51,0x54,0x4a]  # KC 音階
for kc in scale:
    out.write(f"28 {kc:02x} 0\n30 00 0\n08 78 25000\n08 00 5000\n")
out.close()
print(f"voice{vn} idx={idx} confb={confb:#x} dtmul={list(dtmul)} tl={list(tl)} ar={list(ar)}")
