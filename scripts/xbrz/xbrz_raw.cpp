// Minimal xBRZ command-line driver. Build next to the xBRZ sources (xbrz.cpp, xbrz.h, xbrz_config.h, xbrz_tools.h)
// from https://github.com/ioistired/xbrz.py/tree/master/lib, with the dummy_module.cpp include removed from xbrz.cpp:
//   g++ -O2 -std=c++17 -w xbrz_raw.cpp -o xbrz_raw
// usage: xbrz_raw factor w h in.raw out.raw   (raw = uint32 0x00RRGGBB per pixel)
#include "xbrz.cpp"
#include <cstdio>
#include <cstdlib>
#include <vector>
int main(int c, char** v) {
    size_t f = atoi(v[1]); int w = atoi(v[2]), h = atoi(v[3]);
    std::vector<uint32_t> src(w * h), trg(w * h * f * f);
    FILE* in = fopen(v[4], "rb"); fread(src.data(), 4, src.size(), in); fclose(in);
    xbrz_scale_defaults(f, src.data(), trg.data(), w, h, ColorFormat::RGB);
    FILE* out = fopen(v[5], "wb"); fwrite(trg.data(), 4, trg.size(), out); fclose(out);
}
