#!/bin/bash
# 組裝 Windows zip:xu4.exe + DLL(u4cht/win)+ modules/cjk/遊戲資料(u4cht/xu4-allegro)+ run.bat
# 用法:bash dist/win/make-zip.sh [輸出.zip]
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-/tmp/u4-cht-windows-x64.zip}"
OUT="$(realpath -m "$OUT")"          # 解析為絕對路徑(下方 cd 到 tmp 再 zip,相對 OUT 會失效)
D="$ROOT/build_tmp/u4-cht-windows"; mkdir -p "$D"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  D_WIN="$(cygpath -m "$D")"
else
  D_WIN="$D"
fi
# exe + DLL
MSYS_NO_PATHCONV=1 docker run --rm -v "$D_WIN":/out --entrypoint bash u4cht/win -c \
  'cp /work/u4/xu4.exe /work/dll/*.dll /out/'
# 平台無關資料(從 Linux build)
MSYS_NO_PATHCONV=1 docker run --rm -v "$D_WIN":/out --entrypoint bash u4cht/xu4-allegro -c '
  cp /build/xu4/Ultima-IV.mod /build/xu4/U4-*.mod /build/xu4/render.pak /out/
  cp /build/xu4/cjk_font*.bin /build/xu4/u4_cht.tab /out/
  cp /build/xu4/ultima4.zip /build/xu4/u4upgrad.zip /out/ 2>/dev/null || true'
# run.bat(字形:set U4CHT_FONT=firefly 再執行)
cat > "$D/run.bat" <<'BAT'
@echo off
rem 字形切換:set U4CHT_FONT=firefly  (或 kai),省略=Noto
xu4.exe -s 2 --filter xBRZ %*
BAT
unix2dos "$D/run.bat" 2>/dev/null || sed -i 's/$/\r/' "$D/run.bat"
cat > "$D/README.txt" <<'TXT'
Ultima IV: Quest of the Avatar 繁體中文版 (xu4 640x400 2x)

雙擊 run.bat 開始。

遊戲中熱鍵:
  F2 = 切換 EGA / VGA 美術
  F3 = 切換解析度(tile 物理放大)

字形切換:執行前 set U4CHT_FONT=firefly(或 kai),省略=Noto。
TXT
rm -f "$OUT"          # zip 對既有檔是「附加」,不先刪會疊加上一版內容(重複目錄、體積翻倍)
python -c "import zipfile, os, sys; zipf = zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED); [zipf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), os.path.dirname(sys.argv[2]))) for r, d, fs in os.walk(sys.argv[2]) for f in fs]" "$OUT" "$D"
rm -rf "$ROOT/build_tmp"
echo "→ $OUT ($(du -h "$OUT" | cut -f1))"
