---
description: 每週成效檢討：讀 Search Console 與收益資料，產出本週投報率最高的行動並分派給各 agent
argument-hint: [站名]
---

站名：$ARGUMENTS（未提供時用 `coffee-demo`）。

1. 交給 `growth-analyst`：讀取 `sites/<站名>/data/` 下最新的 Search Console 匯出與收益 CSV（找不到就請我提供），執行 `seoengine report` 寫入 `sites/<站名>/reports/<今天日期>.md`。
2. 從報告中挑出最多 5 個行動，依「預估多拿的點擊 × 該頁每點擊收益」排序，每項標明負責 agent。
3. 把行動清單給我確認。我同意後，再依序交給對應 agent 執行；修改到 `src/seoengine/` 的一律經過 `tdd-guardian`。
