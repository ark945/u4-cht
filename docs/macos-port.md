# macOS 原生移植手記(xu4 + faun)

> 上游 [xu4](https://github.com/xu4-engine/u4) 與它用的音訊庫 [faun](https://codeberg.org/wickedsmoke/faun)
> 本來都**沒有 macOS 支援**。這份手記記錄怎麼從「在 macOS 上完全編不過」一路補到
> 「Apple Silicon 上 build + 連結 + 打包成自包含 `.app`」,以及每一層卡關是怎麼被下一次
> CI 失敗暴露出來的。

整個移植在 GitHub Actions 的 macOS runner 上原生進行(Linux 無法可靠跨編 Mach-O),
每改一層就重跑一次、用編譯/連結錯誤定位下一層。最後揭出**五層**上游缺口,依被發現的順序:

## 第 0 層:為什麼非得在 mac 上 build

xu4 的 `.app` 是 Mach-O + 要連 Homebrew 的 Allegro/vorbis 等 arm64 dylib,Linux 跨編不可靠。
所以走 `macos-14`(Apple Silicon)/ `macos-13`(Intel)runner 原生建置。Boron(引擎用的腳本 VM)
與 faun 由源碼建,U4 為 freeware → `make download` 取遊戲資料一併打包。

第一個非 GL 的雷在 Boron:它預設 `PREFIX=/`,`make install` 要寫 `/lib` `/share` —— macOS 的
根目錄受 SIP 唯讀。改 `make DESTDIR=/usr/local install`(對應 Linux 的 `DESTDIR=/usr`)即過。

## 第 1 層:faun 沒有 macOS 音訊後端

faun 的 `faun.c` 只在 `ANDROID` / `__linux__`(PulseAudio)/ `_WIN32`(WASAPI)三種平台 include
對應的 `sys_*.c`,其餘 `#error "Unsupported system"`。macOS 沒有後端。

補法:自寫 [`patches/mac/sys_coreaudio.c`](../patches/mac/sys_coreaudio.c),用 **AudioQueue** 實作
faun 的 7 個 `sysaudio_*` 介面。關鍵是語意對齊 —— faun 的 mixer 執行緒以 **blocking-push** 模型
反覆呼叫 `sysaudio_write()` 推已混音 PCM,裝置吃不下就阻塞(PulseAudio 版靠 `pa_stream_writable_size`
等待)。AudioQueue 是 callback/pull 模型,用 **buffer pool + dispatch 號誌**橋接:空閒 buffer
用完則 `sysaudio_write` 阻塞,callback 播完一塊就歸還並 signal。faun 系統 voice 固定
`FAUN_F32 / 立體聲 / 44100`,ASBD 照映即可。

faun.c 的平台 `#elif` 鏈加一條 `defined(__APPLE__)` → include 本檔。

## 第 2 層:faun 訊息層的逾時用了 macOS 沒有的 `sem_timedwait`

補完後端,連結階段冒出 `undefined: _tmsg_setTimespec / _tmsg_popTimespec`。

追下去:`faun.c` **無條件**用 timespec 版的 timeout API(`MsgTime ts` + `tmsg_setTimespec` +
`tmsg_popTimespec`)。但 `tmsg.c` 只為**非-Apple 的 POSIX**定義 `MsgTime`(= `struct timespec`),
且 `tmsg_popTimespec` 的 POSIX 路徑用 `sem_timedwait` —— **macOS 沒有 `sem_timedwait`**,而且
Apple 分支的號誌是 `dispatch_semaphore_t`、不是 `sem_t`。

(中途走了個彎:tmsg.c 另有一條 `#ifdef TMSG_WAIT_MS` 的 MS 版路徑,且有 `__APPLE__` 的 dispatch
實作 —— 看起來像「macOS 就該定義它」。但定義 TMSG_WAIT_MS 後 faun **不呼叫**那條路徑,反而讓
timespec 函式整段不編譯 → 同樣 undefined。所以 TMSG_WAIT_MS 是錯的旋鈕。)

正解:
- `__APPLE__` 補 `typedef struct timespec MsgTime;`(上游漏定義)。
- `tmsg_popTimespec` 加 `__APPLE__` 分支:`dispatch_semaphore_wait(reader, dispatch_walltime(ts, 0))`
  —— `dispatch_walltime` 把絕對牆鐘 `struct timespec` 轉成 dispatch 的逾時點,回非零即逾時。
- `tmsg_setTimespec` 不用改:它的 POSIX 路徑走 `clock_gettime(CLOCK_REALTIME)`,macOS 原生可用。

## 第 3 層:頂層 Makefile 在 Darwin 選到壞掉的 `Makefile.macosx`

faun 過了,換 xu4 本體:`make` 報 `No rule to make target 'macosx/SDLMain.m'`。

xu4 頂層 Makefile `uname == Darwin` 時用 `Makefile.macosx` —— 那是一份**舊的 SDL 版** mac
makefile,需要早就不存在的 `SDLMain.m`。但真正可用、平台中性的是 Linux 的 `src/Makefile`
(讀 `make.config` 的 `UI=allegro`,本身只是 gcc/clang flag + `-l` 庫,沒有 Linux 專屬)。

補法:`make MFILE_OS=Makefile` 強制用 `src/Makefile`(命令列變數會自動傳遞給 sub-make)。

## 第 4 層:OpenGL —— Apple 舊版 GL 卡在 2.1

換 `src/Makefile` 後,編 `gpu_opengl.cpp` 報一串 `glBindVertexArray` / `glGenVertexArrays` /
`GL_MAP_WRITE_BIT` **undeclared**,還貼心提示「你是不是要 `glBindVertexArrayAPPLE`」。

根因:xu4 渲染器要 **GL 3.3 核心**(VAO、`glMapBufferRange`)。`gpu_opengl.h` 在 `__APPLE__`
分支 include 了 Apple 的舊版 `<OpenGL/gl.h>` —— 那只到 **GL 2.1 + APPLE 擴充**,沒有核心 VAO。
(Windows 走 glad、Linux 走系統 GL header + `-lGL`,各有出路,唯獨 mac 落到舊 header。)

補法:`__APPLE__` 改 include `<OpenGL/gl3.h>`(Apple 核心 GL 3.2,涵蓋這些函式)。
allegro 端本來就用 `ALLEGRO_OPENGL_3_0 | ALLEGRO_OPENGL_FORWARD_COMPATIBLE` 建**核心 context**
—— 與 gl3.h 正好相配。同 TU 內 allegro 又會拉 legacy `gl.h`,靠
`GL_DO_NOT_WARN_IF_MULTI_GL_VERSION_HEADERS_INCLUDED` + `GL_SILENCE_DEPRECATION` 讓兩版共存;
因為 `gpu_opengl.cpp`(→gl3.h)在 include 順序上**先於** allegro 的 gl.h,核心函式由 gl3.h 先宣告。

## 第 5 層:靜態 faun 的連結相依

faun 在 macOS 改**靜態**建(`./configure --static` 產 `libfaun.a`)有兩個理由:避開 faun makefile
的 GNU `-soname`(macOS ld 不認,要 `-install_name`),以及避開它 example 連 `-lpulse`(mac 無)。
代價是靜態庫不帶相依 → xu4 最終連結要自己補:`-lvorbisfile -lvorbis -logg`、
`-framework OpenGL/AudioToolbox/CoreFoundation`、以及 brew 與 `/usr/local` 的 include/lib 路徑
(clang 在 macOS **不**預設搜 `/usr/local/include`,Boron/faun 的 header 都在那)。

連結順序也有講究:`libfaun.a` 的 vorbis 符號要靠**其後**的 `-lvorbisfile` 解,vorbisfile 又要
`-lvorbis -logg` 在更後;CoreAudio 符號靠 `-framework AudioToolbox`。順序排對,`xu4` 連結通過,
Mach-O 帶 `NOUNDEFS`(無未解析符號)。

## 第 6 層:第一個 runtime crash —— Allegro 主執行緒死結(CI 綠 ≠ 跑得起來)

前五層全綠、`.app` 也打包出來了,但在 macOS 26.5.1(Tahoe, Apple Silicon)**一開即崩**。
這是整個移植第一個**只在真機才現形**的問題 —— CI 的 headless runner 只證明「編得過、連得起、
包得出來」,證明不了「開得起來」。

crash log 的 backtrace 一看就懂:

```
Thread 0 Crashed:: Dispatch queue: com.apple.main-thread
0  libdispatch   __DISPATCH_WAIT_FOR_QUEUE__
1  libdispatch   _dispatch_sync_f_slow
2  liballegro    _al_osx_mouse_was_installed
3  liballegro    osx_init_mouse
4  liballegro    al_install_mouse
5  xu4           screenInit_sys → 6 screenInit → 7 servicesInit → 8 main
```

`EXC_BREAKPOINT (SIGTRAP)`。根因是 **Allegro 在 macOS 的主執行緒契約**:`al_install_mouse`
會 `dispatch_sync` 一個區塊到**主佇列(主執行緒)**並等它跑完。但 xu4 的 `main` 本身就跑在
OS 主執行緒上 —— 於是變成「在主執行緒上 dispatch_sync 回主執行緒等自己」,libdispatch 偵測到
這個自我等待,直接 trap(macOS 26 對主佇列死結的偵測更嚴,舊版可能硬撐或卡住,所以同一份
arm64 `.app` 在較舊 mac 跑得到標題、Tahoe 卻崩)。

修法是 macOS 上 Allegro 的**標準要求**(只是上游 xu4 沒做):
- `xu4.cpp` 在 `__APPLE__` 下 `#include <allegro5/allegro.h>` —— 這個標頭會 `#define main
  _al_mangled_main`,把使用者的 `main` 改名。
- 連結 `-lallegro_main` —— 它提供**真正的** `main`:在主執行緒建立 NSApplication,另起一條
  執行緒去呼叫 `_al_mangled_main`(即 xu4 的原 main)。從此使用者程式不在主執行緒跑,
  `al_install_mouse` 的 `dispatch_sync` 到主執行緒就不再是自我等待。

教訓:**跨平台移植,「連結成功」和「能執行」是兩件事**;有平台慣例(此處是 Allegro 必須經
其 main 包裝)時,CI 綠燈只是必要條件,真機跑一遍才是充分條件。

## 解到哪、還沒解到哪(誠實邊界)

- ✅ **Apple Silicon(arm64)**:編譯 → 連結 → 組裝 `.app` → `dylibbundler` 打包相依 dylib →
  ad-hoc 簽章 → zip/dmg → artifact,全綠。`.app` 自包含(遊戲資料、三套 CJK 字型、所有非系統 dylib
  都在裡面),解壓即玩。
- 🟡 **Intel(x86_64)**:同一套修正(brew 前綴差異用 `$(brew --prefix)` 吸收),但 GitHub 的
  `macos-13` runner 供給緊縮、長時間排不到;非 build 問題,等 runner 一有空即補。
- 🟡 **真機 runtime**:headless runner 證明不了「開得起來」。實測 macOS 26.5.1 揭出並修掉了
  第一個真機 crash(第 6 層的 Allegro 主執行緒 SIGTRAP);修正已 build 驗證(連結乾淨、
  `liballegro_main` 已 bundle),但**最終是否正常顯示/出聲仍待真機回測確認**。CoreAudio 後端 +
  allegro 核心 GL context 是 macOS 正確組合。開 `.app` 首次需右鍵「打開」繞 Gatekeeper。

## 方法論(可移植到其他「上游無此平台支援」的移植)

1. **讓 CI 當編譯器**:不能在本機編的目標平台,就用該平台的 runner 原生跑,**用編譯/連結錯誤
   逐層定位**。一次只揭一層,別想一步到位。
2. **push 與 dispatch 之間要等**:`git push` 後立刻 `workflow_dispatch` 可能跑到舊 commit
   (GitHub 還沒註冊新 HEAD)。dispatch 後驗 `headSha == 本地 HEAD`,不一致就重 dispatch。
3. **介面對齊勝過照抄**:補平台後端時,先讀清楚既有後端的**語意契約**(這裡是 blocking-push
   的節流模型),再用目標平台的原語(AudioQueue + dispatch 號誌)對齊,而不是硬塞。
4. **錯的旋鈕會更糊**:`TMSG_WAIT_MS` 看似「就是給 mac 的」,定義下去反而讓需要的函式整段消失。
   先確認**呼叫端實際走哪條路**(grep faun.c 的呼叫),再決定編譯開關。
5. **靜態連結換可攜**:在沒有該平台慣例(`-soname` vs `-install_name`)時,把第三方庫靜態連進來
   常比修它的 shared-lib 規則省事 —— 代價是自己補它的傳遞相依。

> 引擎與資料分離原則照舊:`patches/mac/sys_coreaudio.c` 與 workflow 的 patch 入 repo,
> 上游 xu4/faun(含 `xu4/` 整個 vendored clone)與遊戲資料不入。對應檔:
> [`.github/workflows/build-mac.yml`](../.github/workflows/build-mac.yml)、
> [`patches/mac/sys_coreaudio.c`](../patches/mac/sys_coreaudio.c)。
