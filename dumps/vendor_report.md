# vendor Boron 腳本字串抽取報告

> 自動產生 by `tools/extract_vendor_boron.py`(純文字抽取,不改引擎、不執行 Boron)

## 摘要

- 來源:vendors.b
- 抽出字面總數:300(含純佔位/空白 control 3 筆,不入翻譯表)
- 唯一真文字字串:**278**(其中大括號多行 19 筆)
- 含佔位符(`@ % $ # = $gp`,翻譯保留):**62**

## 佔位符對照

| 符號 | 意義 |
|---|---|
| `@` | 店名 |
| `%` | 店主 |
| `$` | 價格 |
| `#` | 數量 |
| `=` | 物品名 |
| `$gp` | 價格 + gp |

## 樣本(前 25 唯一字串)

| 次數 | kind | 佔位? | 字串 |
|---|---|---|---|
| 2 | quote |  | `\nAnything\nelse?` |
| 2 | quote |  | `\nFine! What else?` |
| 2 | quote | 是 | `\nHow many =s\nwould you wish\nto sell?` |
| 2 | quote |  | `\nHow many would\nyou like?` |
| 2 | quote | 是 | `\nI will give you $gp for that =.\nDeal?` |
| 2 | quote | 是 | `\nI will give you $gp for them.\nDeal?` |
| 2 | quote |  | `\nTake it?` |
| 2 | quote |  | `\nToo bad.` |
| 2 | quote |  | `\nYou don't have that many swine!\n` |
| 2 | quote |  | `\nYou have not the funds for even one!\n` |
| 2 | quote |  | `\nYou sell:` |
| 2 | quote |  | `Anything\nelse?` |
| 2 | quote |  | `Winston` |
| 2 | quote |  | `black stone` |
| 2 | quote |  | `mandrake` |
| 2 | quote |  | `nightshade` |
| 2 | quote |  | `sextant` |
| 2 | quote |  | `skull` |
| 2 | quote |  | `white stone` |
| 1 | quote |  | `\n\nTake it?` |
| 1 | quote |  | `\n\nWill ya buy?` |
| 1 | brace |  | `\n                Unfortunately, I have but only a very small room wit` |
| 1 | brace | 是 | `\n            % says: Ah, the Black Stone.\n            Yes I've heard` |
| 1 | brace | 是 | `\n            % says: For navigation a Sextant is vital... Ask for ite` |
| 1 | brace | 是 | `\n            % says: If thou must know of that evilest of all things.` |