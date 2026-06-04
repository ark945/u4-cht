#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽取 xu4 Boron module 腳本(預設 vendors.b)的 vendor 對白 / 物品名字串,
產出雙語表雛形(en + zh 待填)+ 報告。

純文字靜態抽取,不改引擎、不執行 Boron。處理 Boron 字面:
  - "…"   引號字串(escape 用 ^,如 ^/ 換行、^- tab、^" 引號、^^ caret)
  - {…}   大括號字串(可多行、可巢狀;^{ ^} 為 escape)
  - 跳過 ; 行註解 與 /* */ 區塊註解、'x' 字面、#"x" char

vendor 佔位符(翻譯時保留):@=店名 %=店主 $=價格 #=數量 =name $gp=價格gp ^/=換行

用法:
  python3 tools/extract_vendor_boron.py \
      --files xu4/module/Ultima-IV/vendors.b \
      --out dumps/vendor_bilingual.json \
      --out-report dumps/vendor_report.md
"""
import argparse
import json
import os
import re

CARET = {"/": "\n", "-": "\t", '"': '"', "^": "^", "{": "{", "}": "}",
         "(": "(", ")": ")"}


def decode_caret(s):
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "^" and i + 1 < n:
            out.append(CARET.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def extract_boron_strings(text):
    """回傳 [(line, kind, decoded)]。"""
    res = []
    i = 0
    n = len(text)
    line = 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        # 行註解 ;
        if c == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        # 區塊註解 /* */
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 2
            continue
        # char 字面 'x' / 'word — 跳過單引號 token(不含字串)
        if c == "'":
            i += 1
            continue
        # 引號字串 "…"
        if c == '"':
            start_line = line
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "^" and i + 1 < n:
                    buf.append(text[i]); buf.append(text[i + 1]); i += 2
                    continue
                if text[i] == "\n":
                    line += 1
                buf.append(text[i]); i += 1
            i += 1
            res.append((start_line, "quote", decode_caret("".join(buf))))
            continue
        # 大括號字串 {…}(巢狀)
        if c == "{":
            start_line = line
            depth = 0
            buf = []
            while i < n:
                ch = text[i]
                if ch == "^" and i + 1 < n:
                    buf.append(ch); buf.append(text[i + 1]); i += 2
                    continue
                if ch == "{":
                    depth += 1
                    if depth > 1:
                        buf.append(ch)
                    i += 1
                    continue
                if ch == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                    buf.append(ch); i += 1
                    continue
                if ch == "\n":
                    line += 1
                buf.append(ch); i += 1
            dec = decode_caret("".join(buf))
            # Boron 雙括號 {{…}} 會殘留一層內括號 → 去掉外包的 { }
            st = dec.strip()
            if st.startswith("{") and st.endswith("}"):
                dec = st[1:-1]
            res.append((start_line, "brace", dec))
            continue
        i += 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    raw = []
    for path in args.files:
        text = open(path, encoding="utf-8", errors="replace").read()
        for ln, kind, dec in extract_boron_strings(text):
            raw.append({"file": os.path.basename(path), "line": ln,
                        "kind": kind, "en": dec})

    # 只保留含字母的「真文字」;純佔位/空白/符號標為 control(不入翻譯表)
    def is_text(s):
        return bool(re.search(r"[A-Za-z]", s))

    uniq = {}
    control = 0
    for r in raw:
        if not is_text(r["en"]):
            control += 1
            continue
        e = uniq.setdefault(r["en"], {
            "en": r["en"], "zh": "", "kind": r["kind"],
            "has_placeholder": bool(re.search(r"\$gp|[@%#=]|\$", r["en"])),
            "occurrences": []})
        e["occurrences"].append(f"{r['file']}:{r['line']}")

    entries = sorted(uniq.values(), key=lambda x: (-len(x["occurrences"]), x["en"]))
    ph = sum(1 for e in entries if e["has_placeholder"])
    braces = sum(1 for e in entries if e["kind"] == "brace")

    out = {
        "_meta": {
            "sources": [os.path.basename(p) for p in args.files],
            "mechanism": "Boron module 腳本字面(非 u4read_stringtable / 非硬編 C 字面)",
            "raw_literals": len(raw),
            "control_skipped": control,
            "unique_text_strings": len(entries),
            "with_placeholder": ph,
            "placeholders": {"@": "店名", "%": "店主", "$": "價格",
                             "#": "數量", "=": "物品名", "$gp": "價格gp", "^/": "換行(已解為 \\n)"},
            "note": "en = Boron 字面解碼後文字;zh 待填。佔位符 @ % $ # = $gp 翻譯時保留。",
        },
        "strings": entries,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    L = ["# vendor Boron 腳本字串抽取報告\n",
         "> 自動產生 by `tools/extract_vendor_boron.py`(純文字抽取,不改引擎、不執行 Boron)\n",
         "## 摘要\n",
         f"- 來源:{', '.join(out['_meta']['sources'])}",
         f"- 抽出字面總數:{len(raw)}(含純佔位/空白 control {control} 筆,不入翻譯表)",
         f"- 唯一真文字字串:**{len(entries)}**(其中大括號多行 {braces} 筆)",
         f"- 含佔位符(`@ % $ # = $gp`,翻譯保留):**{ph}**\n",
         "## 佔位符對照\n",
         "| 符號 | 意義 |", "|---|---|",
         "| `@` | 店名 |", "| `%` | 店主 |", "| `$` | 價格 |",
         "| `#` | 數量 |", "| `=` | 物品名 |", "| `$gp` | 價格 + gp |",
         "\n## 樣本(前 25 唯一字串)\n",
         "| 次數 | kind | 佔位? | 字串 |", "|---|---|---|---|"]
    for e in entries[:25]:
        disp = e["en"].replace("\n", "\\n").strip()
        L.append(f"| {len(e['occurrences'])} | {e['kind']} | {'是' if e['has_placeholder'] else ''} | `{disp[:70]}` |")
    open(args.out_report, "w", encoding="utf-8").write("\n".join(L))

    print(f"raw 字面: {len(raw)}  control: {control}  唯一真文字: {len(entries)}  "
          f"含佔位: {ph}  braced: {braces}")
    print(f"→ {args.out}\n→ {args.out_report}")


if __name__ == "__main__":
    main()
