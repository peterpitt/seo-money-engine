# SEO Money Engine — 專案指引

> **接手本專案前，先讀 [`docs/CODEX_HANDOFF.md`](docs/CODEX_HANDOFF.md)。** 它記錄目前的 AdSense 審核、Cloudflare 設定、已完成工作與需要使用者決定的項目。

雙軌（USD / TWD）SEO 變現系統：關鍵字評估 → 內容架構 → 撰寫 → 品質閘門 → 變現 → 建置部署 → 成效分析。
所有回覆與文件使用**繁體中文（台灣用語）**；英文市場的文章內容使用美式英文。

## Agent 分工路由

| 使用者說的話（例） | 交給 | 產出 |
|---|---|---|
| 「這個領域能做嗎」「幫我找關鍵字」「先寫哪篇」「能賺多少」 | `keyword-strategist` | `plans/keyword-plan.md`、更新 `keywords.csv` |
| 「幫我規劃這篇」「給我標題和大綱」 | `content-architect` | draft 文章骨架（標題、meta、slug、H2/H3、FAQ） |
| 「把這篇寫完」「寫英文版」「做一個計算機」 | `bilingual-writer` | 通過 `seoengine check` 的完整文章 |
| 「這篇可以上線嗎」「幫我審」 | `quality-gatekeeper` | PASS / BLOCK 審查報告（只審不改） |
| 「加聯盟商品」「開 AdSense」「為什麼有流量沒收益」 | `monetization-optimizer` | `offers.yaml`、`site.yaml` 變現設定 |
| 「建新站」「建置」「部署」「上線」 | `site-release-engineer` | `public/` 與部署（正式部署前需同意） |
| 「這週該做什麼」「分析 Search Console」「流量怎麼放大」 | `growth-analyst` | `reports/<日期>.md` 與本週行動清單 |
| 任何修改 `src/seoengine/` 的需求、測試失敗、CI 壞掉 | `tdd-guardian` | 先紅後綠的測試與實作 |

需求跨多個階段時，依上表順序逐一交棒；每個 agent 完成後回報產出路徑與下一棒。
完整流程可用 `/seo-pipeline <關鍵字>`，每週檢討用 `/weekly-review <站名>`。

## 必須先問使用者的事

- 正式環境部署、修改 DNS、綁定網域
- 填入真實聯盟網址、AdSense 發布商 ID（只能由使用者提供，**不得自行編造**）
- 申請帳號、接受合約條款、任何付款
- 文章中的第一人稱實測內容——沒有使用者提供的資料就不寫成實測

## 常用指令

```bash
pip install -e ".[dev]"                                   # 安裝
python -m pytest                                          # 全部 BDD + 單元測試
seoengine init sites/<站名>                                # 建新站
seoengine keywords sites/<站名>/keywords.csv --clusters    # 關鍵字排序與分群（也吃 Google Ads 規劃工具匯出檔，非美元加 --fx TWD=0.0307）
seoengine forecast sites/<站名>/keywords.csv --position 3  # 雙幣別收益預估
seoengine brief "<關鍵字>" --project sites/<站名> --market tw
seoengine check sites/<站名> [--include-drafts]            # 品質閘門
seoengine build sites/<站名>                               # 建置到 sites/<站名>/public
seoengine report --gsc gsc.csv --earnings earnings.csv -o report.md
seoengine deploy sites/<站名>                              # 建置＋安全檢查＋部署到 Cloudflare Pages（只上傳 public/）
# 主網域＋子網域（music.<網域>、app.<網域>）：每個網站一個 sites/ 資料夾與 Pages 專案，步驟見 docs/launch-and-subdomains.md
seoengine viz sites/<站名> [--keywords keywords.csv]           # 站長收益儀表板（只給自己看）→ sites/<站名>/dashboard/index.html
# 給訪客的多語言行事曆：site.yaml 的 calendar_page 設定，build 時自動產生 /calendar/<語言>/
# 假日資料的年度更新（哪國何時公布、怎麼加新年度）：docs/holiday-data-maintenance.md
seoengine ads ideas --project sites/<站名>                 # Google Ads 真實搜尋量與出價 → keywords.csv
seoengine trends trending --project sites/<站名>           # Google Trends 熱搜（RSS）
seoengine trends import multiTimeline.csv --project sites/<站名>   # 旺季與最晚上線日
seoengine opportunities --project sites/<站名> --brief 3   # 流量機會排名＋自動草稿
# Google 設定步驟：docs/google-setup.md（developer token 已於 2026-09-09 停用，Keyword Planner 需 Cloud 專案 Basic 等級）
```

## 開發規則（BDD / TDD）

- 行為變更先改 `features/*.feature`（繁中 Gherkin），內部邏輯先寫 `tests/unit/`，確認紅燈再實作。
- 不刪除、不弱化既有測試；覆蓋率維持 90% 以上。
- 發布流程中品質閘門失敗的文章一律不上線；`--force` 只在使用者明確要求時使用。
