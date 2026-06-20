#!/usr/bin/env python3
"""Amiga mus*.bin → WAV,用 snds.bin 取樣當樂器(取代方波,取樣式合成)。
note=MIDI 半音→Paula 重採樣,cmd 低 nibble=時長。取樣取 snds.bin 一段穩定波形。"""
import sys,struct,wave
d=open(sys.argv[1],"rb").read()
snds=open(sys.argv[2],"rb").read()
# 取 snds 一段當樂器波形(找穩定振盪段:跳過 header,取中段 512 樣本)
inst=[struct.unpack("b",bytes([b]))[0]/128.0 for b in snds[2000:2512]]
hdr=[struct.unpack_from(">H",d,i*2)[0] for i in range(8)]
offs=sorted(set(o for o in hdr[2:7] if 0<o<len(d)))+[len(d)]
SR=22050; TICK=0.10
def parse(seg):
    ev=[]; cmd=0
    for b in seg:
        if b&0x80: cmd=b
        elif 0x20<=b<0x40: ev.append((b,(cmd&0x0f)or 4))
    return ev
def render(ev):
    buf=[]
    for note,dur in ev:
        f=440*2**((note-69)/12); n=int(SR*TICK*dur)
        # 取樣重採樣:相位依音高推進,迴圈 inst
        step=f/110.0  # inst 假設基頻 ~110Hz
        for i in range(n):
            pos=(i*step)%len(inst)
            env=min(1.0,(n-i)/(SR*0.05)) if n-i<SR*0.05 else 1.0  # 尾音衰減
            buf.append(inst[int(pos)]*0.3*env)
    return buf
voices=[parse(d[offs[i]:offs[i+1]]) for i in range(len(offs)-1)]
voices.sort(key=len,reverse=True)
tracks=[render(v) for v in voices[:2] if v]
L=max(len(t) for t in tracks)
mix=[0.0]*L
for t in tracks:
    for i,s in enumerate(t): mix[i]+=s
pcm=b"".join(struct.pack("<h",int(max(-1,min(1,s))*32767)) for s in mix)
w=wave.open(sys.argv[3],"wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
w.writeframes(pcm);w.close()
print(f"取樣式合成 {L/SR:.0f}s")
