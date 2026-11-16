---
description: 從一個關鍵字跑完整 SEO 變現流程（評估 → 架構 → 撰寫 → 審查 → 建置），每個階段交給對應 agent
argument-hint: <關鍵字> [站名] [tw|us]
---

對關鍵字「$ARGUMENTS」執行完整流程。參數依序為：關鍵字、站名（預設 `coffee-demo`）、市場（預設依關鍵字語言判斷：中文 → tw，英文 → us）。

依序呼叫下列 agent，**每一步完成後先把產出摘要給我，再進下一步**：

1. `keyword-strategist`：評估此關鍵字的意圖、錢景分數、第 3 名預估月收益，以及同群可一起規劃的長尾詞。若 KD > 60 或屬導航型，停下來問我是否繼續。
2. `content-architect`：建立 draft 骨架，給我 3 個標題候選。
3. `bilingual-writer`：寫完全文，直到 `seoengine check --include-drafts` 該篇 PASS 且分數 ≥ 90。列出需要我補充的實測資料。
4. `quality-gatekeeper`：獨立審查。BLOCK 就回到第 3 步修正（最多兩輪，仍未通過就停下來告訴我原因）。
5. `monetization-optimizer`：確認文中引用的商品都在 `offers.yaml`；缺少的列給我，由我提供真實聯盟連結。
6. `site-release-engineer`：執行測試與 `seoengine build`，回報建置結果。**不要部署**，等我確認。

最後給我一張摘要：文章路徑、品質分數、待我補充的項目、預估月收益（標明幣別）。
