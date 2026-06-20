#!/usr/bin/env bash
# 取得 ymfm(Aaron Giles,BSD-3)+ 編譯 YM2151 render harness。
# ymfm 是外部 library(BSD),不入本 repo;此腳本在 docker 內 clone + 編譯。
# 用法:bash build.sh   (產出 ./render)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --entrypoint bash -v "$HERE:/y" u4cht/xu4-allegro -c '
  cd /tmp && git clone --depth 1 https://github.com/aaronsgiles/ymfm 2>/dev/null
  cp ymfm/src/ymfm*.h ymfm/src/ymfm_opm.cpp ymfm/src/*.ipp /y/
  cd /y && g++ -O2 -I. render.cpp ymfm_opm.cpp -o render
  echo "render 編譯完成"
'
docker run --rm -v "$HERE:/y" u4cht/xu4-allegro chown -R "$(id -u):$(id -g)" /y
