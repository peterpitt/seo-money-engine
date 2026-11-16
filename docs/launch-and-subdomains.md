# 上線計畫：主網域＋子網域

一個網域、多個網站：每個網站一個資料夾、一個 Cloudflare Pages 專案、一個網址，各自部署、互不影響。
目前的網域是 **asusucloud.com**（2026-10-30 在 Cloudflare 購買）。下面的 `<網域>` 就是 `asusucloud.com`。

## 最後的樣子

| 網址 | 網站 | 專案資料夾 | Cloudflare Pages 專案 |
|---|---|---|---|
| `https://<網域>` | 假日行事曆（主網域，放 `ads.txt`） | `sites/holiday-calendar` | `asusu-calendar` |
| `https://www.<網域>` | 301 轉到主網域 | — | 重新導向規則 |
| `https://music.<網域>` | 音樂 | `sites/music` | `asusu-music` |
| `https://app.<網域>` | 公益小幫手 | `sites/app` | `asusu-app` |
| 你的電腦 | 收益儀表板、Google 金鑰 | — | 不上網 |

為什麼用子網域、不用 `<網域>/music`：三個主題無關，分開比較不會稀釋假日網站的主題；而且部署會整個替換網站內容，分開才不會互相覆蓋。想要好記的網址，可以在 Cloudflare 加一條轉址：`<網域>/music` → `https://music.<網域>`。

## 選網域前

1. **在 Cloudflare「註冊網域」搜尋確認可以註冊**。第三方 WHOIS 網站的結果常常不準，以 Cloudflare 為準。
2. **避開讀起來像別人商標的名稱**。例如 `asuspace` 很容易被讀成「ASUS space」，搜尋結果也全是華碩；知名商標持有人可以依 UDRP 程序要求轉移網域。用你自己的品牌（ASUSU）並讓它明顯可辨，風險較低。（這不是法律意見。）
3. `.com` 每年 US$10.46（2026/11/1 起續約 US$11.17），子網域不用另外付錢。

## 第 1 步：主網域上線（假日行事曆）

1. `sites/holiday-calendar/site.yaml` 的 `base_url` 已設為 `https://asusucloud.com`（如果是 `your-domain.example` 這類範例網域，部署工具會拒絕上傳）。
2. 部署：

   ```powershell
   npx wrangler login
   seoengine deploy sites/holiday-calendar
   ```

   第一次會建立 Pages 專案 `asusu-calendar`，先出現在 `asusu-calendar.pages.dev`。
3. Cloudflare 後台 → Workers & Pages → `asusu-calendar` →「自訂網域」→ 新增 `<網域>` 與 `www.<網域>`。
4. 「規則」→「重新導向規則」：`www.<網域>` 301 轉到 `https://<網域>`。

## 第 2 步：Google（只要做一次，涵蓋所有子網域）

- **Search Console**：新增「網域」資源 `<網域>`（不是網址前置字元）。網域資源會**自動包含所有子網域**，只要驗證一次。每個網站各自提交自己的 `sitemap.xml`。
- **AdSense**：在「網站」新增主網域一次。子網域不需要（也不能）另外新增，也不影響廣告投放。`ads.txt` 只放在主網域根目錄，由假日網站提供。
- 每個子網域網站都要有自己的隱私權政策頁，系統建置時會自動產生。

## 第 3 步：新增子網域網站（例如音樂）

1. 建立網站：

   ```powershell
   seoengine init sites/music
   ```

2. 編輯 `sites/music/site.yaml`：
   - `base_url: https://music.<網域>`
   - `deploy: {cloudflare_project: asusu-music}`
   - 範例內容換成自己的。
3. 第一次部署：`seoengine deploy sites/music`。
4. Cloudflare →「自訂網域」新增 `music.<網域>`。網域在 Cloudflare，DNS 紀錄會自動建立。
5. 加進自動部署：`.github/workflows/ci.yml` 的 `SITES` 加上 `sites/music`，`deploy` 的 `matrix.site` 也取消那一行的註解（兩邊要一致，測試會檢查）。
6. 互相連結：每個網站的 `site.yaml` 都加上同一份 `network` 清單，頁尾就會連到其他姊妹站（自己那項不顯示）。

`app.<網域>` 做法相同。如果公益小幫手需要資料庫或登入，靜態網站不夠，再另外規劃（例如 Cloudflare Pages Functions）。

## 上線前要確認的事

- **Suno 音樂**：免費方案做的歌所有權屬於 Suno、只能非商業使用；放在有廣告的網站需要 Pro／Premier 方案做的歌。以 Suno 最新條款為準。
- **公益小幫手**：個人不能對外發起公益募款（《公益勸募條例》，罰 4–20 萬）。捐款請連到已立案團體自己的捐款頁。

## 自動化

推上 GitHub 後，`main` 分支每次更新、以及每週一凌晨，會依 `SITES` 清單：測試 → 每個網站跑品質閘門 → 每個網站各自部署（一個失敗不影響其他）。需要 GitHub Secrets：`CLOUDFLARE_API_TOKEN`（權限「Cloudflare Pages：編輯」）、`CLOUDFLARE_ACCOUNT_ID`。
