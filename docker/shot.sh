#!/bin/bash
# Headless 截圖:Xvfb + Mesa 軟體 GL 跑 xu4,抓 root window 存 /out/screen.png
set -u
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export ALLEGRO_AUDIO_DRIVER=none

WAIT="${1:-8}"          # 啟動後等幾秒再截圖
SCALE="${2:-3}"         # xu4 顯示縮放(1-5);Xvfb 尺寸隨之對齊
XU4_ARGS="${3:-}"       # 額外 xu4 參數(如 --skip-intro)

W=$((320 * SCALE)); H=$((200 * SCALE))
Xvfb :99 -screen 0 ${W}x${H}x24 -ac +extension GLX +render -noreset >/out/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 2

cd /build/xu4
./src/xu4 -q -v -s "$SCALE" $XU4_ARGS >/out/xu4.log 2>&1 &
XU4_PID=$!

sleep "$WAIT"

if import -window root /out/screen.png 2>/out/import.log; then
  echo "screenshot OK (import)"
elif xwd -root -silent 2>/dev/null | convert xwd:- /out/screen.png 2>>/out/import.log; then
  echo "screenshot OK (xwd)"
else
  echo "screenshot FAILED"; cat /out/import.log
fi

kill "$XU4_PID" 2>/dev/null
kill "$XVFB_PID" 2>/dev/null
echo "--- xu4.log tail ---"; tail -15 /out/xu4.log
