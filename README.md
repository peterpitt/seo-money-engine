# SEO Money Engine

雙軌（**USD** 歐美高購買力市場 / **TWD** 台灣在地市場）SEO 變現系統。
把「選題 → 寫作 → 品質把關 → 變現 → 上線 → 成效回饋」做成可重複執行、有測試保護的流水線，並配置一組分工明確的 Claude Code agent 來執行。

```
keywords.csv ─▶ 錢景排序／分群／收益預估 ─▶ 文章骨架（brief）
                                              │
                         Markdown + 變現短碼 ◀─┘
                                │
                         品質閘門（未通過不發布）
                                │
   聯盟跳轉頁 /go/ ◀── 建置 ──▶ 文章頁（AdSense 版位、內部連結、JSON-LD、hreflang）
                                │      sitemap.xml ／ feed.xml ／ robots.txt ／ ads.txt
                                ▼
                Search Console + 收益 CSV ─▶ 週報（擊殺距離詞、點閱率落差、各幣別收益）
```

## 快速開始

```bash
pip install -e ".[dev]"
python -m pytest                              # BDD + 單元測試

seoengine init sites/my-site                  # 建立新站（含範例文章、聯盟商品表、關鍵字表）
# 編輯 sites/my-site/site.yaml 的 base_url
seoengine keywords sites/my-site/keywords.csv --max-kd 40 --clusters
seoengine check sites/my-site
seoengine build sites/my-site                 # → sites/my-site/public/
python -m http.server 8000 -d sites/my-site/public
```

`sites/coffee-demo/` 是已建立好的示範站（中英雙語、3 篇文章、虛構的示範聯盟商品）。

`sites/holiday-calendar/` 是國定假日行事曆站：美國、阿聯、義大利、日本 2026–2027 假日（`data/holidays/*.yaml`，已與官方來源及 python-holidays 交叉比對）＋ 4 篇英文、1 篇繁中文章。每年只要更新資料檔，頁面就會自動重建。阿聯的伊斯蘭節日在官方公告後，要把日期改成公告日並把 `status` 改為 `official`。

## 系統功能

| 模組 | 做什麼 |
|---|---|
| `keywords` | 讀自家 CSV 或 Google Ads 關鍵字規劃工具匯出檔（UTF-16／Big5／UTF-8、Tab 或逗號、搜尋量範圍取幾何中間值、台幣出價依 fx_to_usd 換成美元）；中英文搜尋意圖判斷（資訊／商業調查／交易／導航）、錢景分數 = 量 × CPC × 意圖權重 × (1−KD)²、主題分群找支柱頁 |
| `revenue` | 依目標排名估算點擊 → AdSense + 聯盟收益，**美金與台幣分開加總、永不混算** |
| `quality` | 品質閘門：薄內容、AI 套話（中英）、標題缺關鍵字、內文 H1、圖片缺 alt → 擋下；標題／描述長度（中文字算 2 寬）、段落過長、H2 不足 → 警告 |
| `monetize` | `[[offer:id]]` `[[cta:id]]` `[[compare:a,b]]` 短碼 → `rel="sponsored"` 連結、CTA 卡、比較表（手機自動轉卡片）；`/go/<id>/` noindex 跳轉頁；H2 前插入 AdSense 並控制數量與間距；自動揭露聲明；`ads.txt` |
| `linking` | 自動把站內其他文章的目標關鍵字連過去（同語言、每篇上限 3 個、跳過標題與既有連結） |
| `schema` | Article、BreadcrumbList、FAQPage JSON-LD |
| `calendar` | 國定假日資料檔 → `[[holidays:jp:2027]]` 假日表（自動算星期、標示預估／移假）、`[[longweekends:jp:2027]]` 連假與請假建議（每請 1 天至少換 3 天）、`[[countdown:jp]]` 下一個假日倒數、`[[remaining:jp:2026]]` 該年度還沒過的假日（建置當天計算，瀏覽器端每天自動更新，不要在內文寫死「還剩幾個」） |
| `viz` | `seoengine viz <網站>` 產生可離線開啟的動畫儀表板：各國假日時間軸（播放／拖曳日期、連假與請假串連）、SEO 流水線粒子動畫（實際文章與閘門數字）、USD/TWD 雙軌收益曲線（拖動排名，數字由引擎計算） |
| `calendar_page` | 給訪客的多語言假日行事曆：國家區塊切換、下一個假日倒數、全年清單、連假與請假建議。site.yaml 設 `calendar_page`（countries / languages / year），每個語言一個網址（`/calendar/`、`/calendar/ja/`…，第一個語言為預設），阿拉伯文自動由右至左；翻譯放 `data/holidays/i18n.yaml`，各國假日優先顯示當地原名 |
| `google` | **Google Trends**：熱門 RSS（`trends trending`）、探索頁 CSV 旺季分析（`trends import`）、官方 API 預留接口；**Google Ads Keyword Planner**：OAuth 授權（`ads auth`）、真實搜尋量與出價（`ads ideas`）；**流量機會**（`opportunities --brief N`）合併三者並自動建草稿。設定步驟見 [docs/google-setup.md](docs/google-setup.md) |
| `deploy` | `seoengine deploy <網站>`：重新建置、檢查 public/ 不含儀表板／金鑰／關鍵字檔，再用 wrangler 部署到 Cloudflare Pages；建置時輸出 `_headers`（安全標頭、快取、/go/ 不收錄）。上線與子網域步驟見 [docs/launch-and-subdomains.md](docs/launch-and-subdomains.md) |
| `privacy` | 建置時自動產生英文 `/privacy/`、中文 `/privacy/zh-tw/` 隱私權政策（含 AdSense 規定的 cookie 揭露與退出連結，依是否啟用 AdSense／GA4 調整），全站頁尾連到同語言版本；`site.contact_email` 可加上聯絡信箱 |
| `site` | 靜態網站：canonical、hreflang + x-default、OG、`max-image-preview:large`（Discover）、sitemap、RSS、robots、GA4 聯盟點擊事件、404 |
| `report` | 讀 Search Console 匯出（中英文欄位皆可）與收益 CSV，找擊殺距離詞（8–20 名）、點閱率落差、各頁各幣別收益 |

## Agent 團隊（Claude Code）

用 Claude Code 開啟此資料夾即可呼叫。分工路由寫在 [`CLAUDE.md`](CLAUDE.md)。

| Agent | 負責 |
|---|---|
| `keyword-strategist` | 階段一：市場與關鍵字金礦評估、雙軌選題、收益預估 |
| `content-architect` | 階段二：3 個高 CTR 標題、meta、slug、H2/H3 大綱、FAQ、draft 骨架 |
| `bilingual-writer` | 階段三：台灣繁中／美式英文全文，寫到通過品質閘門 |
| `quality-gatekeeper` | 發布前獨立審查（事實、捏造、E-E-A-T、AdSense／揭露合規），**只審不改** |
| `monetization-optimizer` | 聯盟商品表、AdSense 設定、CTA 與比較表擺位優化 |
| `site-release-engineer` | 建站、建置、技術 SEO 驗證、部署（正式部署前需你同意） |
| `growth-analyst` | 階段四：每週成效分析、內部連結、Schema、Discover 與社群擴散 |
| `tdd-guardian` | 引擎程式的任何修改都走 BDD/TDD：先紅燈再綠燈 |

斜線指令：
- `/seo-pipeline <關鍵字> [站名] [tw|us]` — 一個關鍵字跑完評估 → 架構 → 撰寫 → 審查 → 建置（不自動部署）
- `/weekly-review [站名]` — 讀 Search Console 與收益資料，排出本週投報率最高的行動並分派

## BDD / TDD

- `features/*.feature`：繁中 Gherkin 規格（關鍵字評估、品質閘門、變現、網站建置、成效報告）
- `tests/bdd/`：pytest-bdd 步驟定義；`tests/unit/`：單元測試（含 agent 定義的回歸測試）
- CI（`.github/workflows/ci.yml`）：測試 + 覆蓋率 ≥ 90% → 品質閘門 → `seoengine deploy` 到 Cloudflare Pages（需 GitHub Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`）

## 上線前必做

1. `site.yaml`：`base_url`、站名、作者。
2. `offers.yaml`：把示範商品換成你從聯盟後台拿到的**真實**推廣連結、價格與優缺點。
3. 範例文章是示範內容，請改成你自己的實測經驗後再發布（E-E-A-T 的 Experience 只能來自你）。
4. AdSense 審核通過後填 `adsense.client`；GA4 填 `analytics.ga4`。
5. 部署後到 Search Console 提交 `sitemap.xml`。

## 關於收益預估

`seoengine forecast` 用「單一主關鍵字 × 目標排名的點閱率」估算，是**保守的下限參考**：實際上一篇排名穩定的文章通常會同時接到大量長尾查詢。
預設的 RPM、聯盟點擊率、轉換率與佣金都是起始假設（`src/seoengine/revenue.py` 的 `DEFAULT_ECONOMICS`），上線 2–3 個月後請用實際報表校正。新站從發布到穩定排名通常需要數個月，請以此規劃。
