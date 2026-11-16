# 串接 Google Trends 與 Google Ads 設定教學

最後查證：2026-10-24（Google Ads API v26、google-ads Python 函式庫 34.0）

## 先看整體流程

```
① seoengine ads ideas        Google Ads Keyword Planner → 真實的月搜尋量、CPC 出價（寫入 keywords.csv）
② seoengine trends trending  Google Trends 熱門 RSS → 正在升溫、跟網站主題相關的熱搜
③ seoengine trends import    Google Trends 探索頁匯出的 CSV → 旺季月份、最晚上線日
④ seoengine opportunities    合併①②③排出「流量機會」，--brief N 自動產生前 N 名的文章骨架
⑤ seoengine viz              站長收益儀表板顯示流量機會、熱搜與真實收益預估
```

②③ 不需要任何帳號，現在就能用；① 需要以下一次性設定。

---

## Google Trends

### 熱門搜尋 RSS（免金鑰）

```powershell
seoengine trends trending --project sites/holiday-calendar
```

- 國家與主題關鍵字讀 `site.yaml` 的 `trends.geos`、`trends.include`，也可以用 `--geo JP --include "golden week,連休"` 臨時指定。
- 每個國家的 RSS 大約只有最新 10 筆熱搜，建議每天跑一次（排程見最後一節），才不會錯過短暫的熱度。
- 結果存在 `sites/<站>/data/trending.json`。

### 探索頁 CSV（看旺季）

1. 打開 [Google Trends 探索](https://trends.google.com/trends/explore)，輸入關鍵字（例如 `public holidays`），地區選國家，時間選「過去 5 年」。
2. 在「一段時間內的熱度」圖表右上角按下載（CSV）。
3. 匯入：

```powershell
seoengine trends import Downloads\multiTimeline.csv --project sites/holiday-calendar
```

會算出旺季月份與「最晚上線日」（旺季開始前 6 週，給 Google 收錄與排名爬升的時間），存在 `data/seasonality.json`。

### 官方 Google Trends API

目前是**封閉 alpha**，需要[申請](https://developers.google.com/search/apis/trends)，規格只對核准者公開。程式已預留接口（`seoengine trends api`），核准後把官方文件交給 Claude 實作即可，其他流程不用改。

---

## Google Ads Keyword Planner（一次性設定）

> **2026 年 9 月 9 日起的重要變動**：developer token 已停用（有填也會被忽略），
> API 權限改成綁在 Google Cloud 專案上。網路上較舊的教學會叫你去 Google Ads「API 中心」申請 token——**不要照做**，那裡的申請已不再處理。

### 1. 準備 Google Ads 帳戶

- 用一般 Google Ads 帳戶即可，**不需要真的投放廣告**。
- 記下右上角的 10 碼客戶 ID（例如 `123-456-7890`）。

### 2. 建立 Google Cloud 專案並啟用 API

1. 到 [Google Cloud Console](https://console.cloud.google.com/) 建立專案。
2. 「API 和服務」→「程式庫」→ 搜尋 **Google Ads API** → 啟用。啟用後專案會自動取得 **Test** 等級（只能存取測試帳戶）。

### 3. 申請 Basic 存取等級（Keyword Planner 必要）

| 等級 | 能不能用 Keyword Planner |
|---|---|
| Test | 不行（只能用測試帳戶，測試帳戶沒有搜尋量資料） |
| Explorer | **不行**（規劃類服務被封鎖） |
| **Basic** | **可以**，每天 15,000 次操作，本工具一次查詢只用幾次 |
| Standard | 可以，需人工審核 |

1. 先在 Cloud 專案完成**品牌驗證**（brand verification）。
2. 到 Cloud Console 的 Google Ads API「總覽」頁申請 Basic，官方說明通常幾分鐘內自動審核。
3. 你的 Google 帳號需要專案的 Owner／Editor 等權限才能申請。

### 4. 建立 OAuth 用戶端

1. 「API 和服務」→「憑證」→「建立憑證」→「OAuth 用戶端 ID」→ 應用程式類型選**電腦版應用程式**。
2. 下載 JSON（例如 `client_secret_xxx.json`），放在專案外或 `secrets\` 資料夾。

### 5. 授權並產生設定檔

```powershell
pip install -e ".[google]"
seoengine ads auth --client-secrets secrets\client_secret_xxx.json --customer-id 123-456-7890
```

瀏覽器會打開 Google 登入頁，用有權存取該 Google Ads 帳戶的帳號同意授權。完成後會產生 `secrets\google-ads.yaml`：

- `secrets\` 資料夾會自動加上 `.gitignore`，**不會被推上 GitHub**。
- 如果你是透過管理員帳戶（MCC）存取，加上 `--login-customer-id <管理員帳戶ID>`。

### 6. 抓真實關鍵字數據

```powershell
seoengine ads ideas --project sites/holiday-calendar
```

- 不加參數時依序跑 `site.yaml` 的 `google.seeds`（美國、阿聯、義大利、日本、台灣各一組）。
- 臨時查一組：`seoengine ads ideas --project sites/holiday-calendar --seed "golden week 2027" --geo JP --lang en`
- 國家與語言常數由 API 即時查詢，不用自己找 ID。
- **帳戶幣別不是美元**（例如台灣帳戶是 TWD）時，先在 `site.yaml` 設定匯率，否則會拒絕寫入（避免錯誤的錢景分數）：

```yaml
google:
  fx_to_usd: {TWD: 0.031}   # 請填當天匯率
```

寫入 `keywords.csv` 的欄位：

| 欄位 | 來源 |
|---|---|
| volume | 平均月搜尋量（avg_monthly_searches） |
| cpc | 首頁出價高低的中間值，換算成美元 |
| difficulty | **廣告**競爭指數 0–100（競爭度的代理指標，不等於 SEO 難度） |
| source | `google-ads`（儀表板會顯示「Google Ads 真實數據」） |

---

## 排出流量機會

```powershell
seoengine opportunities --project sites/holiday-calendar --brief 3
seoengine viz sites/holiday-calendar
```

- 分數 = 錢景分數 × 熱搜中 1.5 倍 × 旺季將至（60 天內要上線）1.2 倍。
- 已經有文章的主題排到最後並標示「已有文章」，不會重複產生。
- `--brief 3` 為前 3 個新機會建立草稿（`draft: true`），交給 `bilingual-writer` 寫完再發布。

## 每天自動抓熱搜（Windows 工作排程器）

```powershell
schtasks /Create /SC DAILY /ST 08:30 /TN "seoengine-trends" /TR "cmd /c cd /d C:\Users\tt\Downloads\seo-money-engine\seo-money-engine && ..\.venv\Scripts\python.exe -m seoengine.cli trends trending --project sites/holiday-calendar && ..\.venv\Scripts\python.exe -m seoengine.cli opportunities --project sites/holiday-calendar && ..\.venv\Scripts\python.exe -m seoengine.cli viz sites/holiday-calendar"
```

（`opportunities` 需要先跑過一次 `ads ideas` 產生 keywords.csv。）
