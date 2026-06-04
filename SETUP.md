# U4-cht 開發環境設定

本 repo 只納管**自有產出**(PLAN、Dockerfile、腳本、docs)。上游引擎 `xu4/` 與參考用 `u4remastered/`
**不入庫**(見 `.gitignore`),由下列指令重建。

## 1. 取得上游

```bash
# xu4 引擎(Allegro 5 後端 / 跨平台 C++)
git clone https://github.com/xu4-engine/u4.git xu4
cd xu4 && git submodule update --init --recursive && cd ..

# (可選)u4remastered:僅作對話字料 oracle
git clone https://github.com/MagerValp/u4remastered.git u4remastered
```

## 2. 建置 xu4(Allegro 5,Docker)

```bash
# 建置引擎 image(自源碼建 Boron + Faun,make download 自動抓 freeware U4 資料)
docker build -f docker/Dockerfile.zh -t u4cht/xu4-allegro xu4
```

產物(image 內 `/build/xu4/`):`src/xu4`(vDR-1.0)、`Ultima-IV.mod`、`U4-Upgrade.mod`、`render.pak`、`ultima4.zip`、`u4upgrad.zip`。

## 3. headless 截圖 pass/fail loop

```bash
# 建置測試 image(xvfb + Mesa 軟體 GL + ImageMagick)
docker build -f docker/Dockerfile.test -t u4cht/xu4-test docker

# 跑遊戲並截圖:<等待秒數> <scale>
mkdir -p /tmp/u4shot
docker run --rm -v /tmp/u4shot:/out u4cht/xu4-test 22 3
# → /tmp/u4shot/screen.png
```

## 檔案

| 路徑 | 說明 |
|---|---|
| `PLAN.md` | 評估 + 執行計畫(權威文件) |
| `docker/Dockerfile.zh` | xu4 Allegro 5 Linux build |
| `docker/Dockerfile.test` | 在上者之上加 headless 截圖工具 |
| `docker/shot.sh` | Xvfb + llvmpipe 跑 xu4 並截圖 |
| `docs/` | P3 hook 盤點等工程文件 |
