// YM2151 (OPM) register-event → WAV 渲染 harness,用 ymfm(Aaron Giles)。
// 輸入:每行 "addr data wait"(hex addr/data,十進位 wait=寫完後推進的取樣數)。
// 輸出:mono 16-bit WAV @ ymfm 算出的 sample rate(X68000 clock 4MHz)。
// 編譯:g++ -O2 -I. render.cpp ymfm_opm.cpp ymfm_misc.cpp -o render
#include "ymfm_opm.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <vector>
#include <string>

class Interface : public ymfm::ymfm_interface {};

static void put32(std::vector<uint8_t>& v, uint32_t x){ for(int i=0;i<4;i++) v.push_back(x>>(8*i)); }
static void put16(std::vector<uint8_t>& v, uint16_t x){ v.push_back(x&0xff); v.push_back(x>>8); }

int main(int argc, char** argv){
    if(argc<3){ fprintf(stderr,"usage: render <events.txt> <out.wav> [clock=4000000]\n"); return 1; }
    uint32_t clock = argc>3 ? (uint32_t)atoi(argv[3]) : 4000000;
    Interface intf; ymfm::ym2151 chip(intf); chip.reset();
    uint32_t sr = chip.sample_rate(clock);
    std::vector<int16_t> pcm;
    ymfm::ym2151::output_data out;
    FILE* f = fopen(argv[1],"r");
    if(!f){ fprintf(stderr,"cannot open %s\n",argv[1]); return 1; }
    unsigned addr,data,wait;
    long writes=0;
    while(fscanf(f,"%x %x %u",&addr,&data,&wait)==3){
        chip.write_address((uint8_t)addr);
        chip.write_data((uint8_t)data);
        writes++;
        for(unsigned i=0;i<wait;i++){
            chip.generate(&out,1);
            int32_t s=(out.data[0]+out.data[1])/2;
            s = s>>1;
            if(s>32767)s=32767; if(s<-32768)s=-32768;
            pcm.push_back((int16_t)s);
        }
    }
    fclose(f);
    std::vector<uint8_t> h;
    uint32_t bytes=(uint32_t)pcm.size()*2;
    for(char c:std::string("RIFF")) h.push_back(c); put32(h,36+bytes);
    for(char c:std::string("WAVE")) h.push_back(c);
    for(char c:std::string("fmt ")) h.push_back(c); put32(h,16); put16(h,1); put16(h,1);
    put32(h,sr); put32(h,sr*2); put16(h,2); put16(h,16);
    for(char c:std::string("data")) h.push_back(c); put32(h,bytes);
    FILE* o=fopen(argv[2],"wb"); fwrite(h.data(),1,h.size(),o);
    fwrite(pcm.data(),2,pcm.size(),o); fclose(o);
    fprintf(stderr,"%ld writes -> %zu samples @ %uHz -> %s\n",writes,pcm.size(),sr,argv[2]);
    return 0;
}
