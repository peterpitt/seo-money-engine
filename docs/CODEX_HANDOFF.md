# Codex / Claude 接手紀錄

最後更新：2026-11-16（Asia/Taipei）

## 目前網站

- 正式網站：`https://asusucloud.com`
- Cloudflare Pages 專案：`asusu-calendar`
- 原始專案：`sites/holiday-calendar/`
- 建置：`seoengine build sites/holiday-calendar`
- 正式部署：`seoengine deploy sites/holiday-calendar`（**必須先取得使用者同意**）
- AdSense 發布商 ID 已在 `site.yaml` 與 `ads.txt` 設定；網站仍在 Google 審核中，請勿刪站或重送審。

## 已完成（本機原始碼）

- Cloudflare 已有 `HTTP → HTTPS` 與 `www → asusucloud.com` 的 301 規則。
- Cloudflare 免費 Email Routing 已啟用；`hello@asusucloud.com` 會轉寄到站長已驗證的收件匣。
- 建置器會產生中英文 About、Contact、Terms、Privacy 頁面，且所有頁尾都會連到它們。
- About 頁說明編輯原則與未來日期的標示方式；Terms 頁包含一般資訊與外部連結的免責說明。
- 文章已補齊或強化資料來源段落；優先使用政府、主管機關、交易所等第一手來源。
- 行事曆頁桌機版已有「節慶倒數」側欄：圓形國家按鈕可切換資訊卡；卡片只呈現下一個與近期假日，旅遊資源顯示「連結準備中」，沒有新增未驗證的外部連結。手機版保留既有雙欄國家卡片。

## 2026-11-16 審核前修正（已於 11-16 14:39 部署，線上抽查通過）

以下五項外部審查意見都已修正並上線。部署後又把四篇「剩餘假日」段落裡點名假日的引言拿掉（美國那句仍提到已過的 Veterans Day），**這個小修正還需要再部署一次**：

1. **找不到作者、About、Contact、Terms**：信任頁與頁尾連結先前已完成但沒部署。這次另外讓文章署名連到 About（`rel="author"`）、有更新時同時顯示發布日，並新增 `site.author_type`（本站設為 `organization`，結構化資料的作者如實標成 Organization 並帶 About 網址）。
2. **「2026 剩餘假日」寫 3 個、表格列 11 個**：新增短碼 `[[remaining:<國碼>:<年>]]`，只列建置當天還沒過的假日，瀏覽器端每天自動收起已過的列並更新數字。us／italy／japan（英、中）四篇已改用，內文不再寫死「還剩幾個」；uae 那句也改成不會過期的說法。五篇的 `updated` 改為 2026-11-16。
3. **標題 2027、預設分頁像是 2026**：瀏覽器裡預設本來就是 2027，但靜態 HTML 把 2026 區塊排在前面。現在預設年份的區塊排最前（年份按鈕仍照年份順序）。
4. **「選國家看所有假日」但靜態內容只有美國**：其他國家的面板原本帶 `hidden`。現在靜態 HTML 九國面板都看得到，有 JavaScript 時才收合成分頁（`<html class="cp-js">` 避免閃爍）；沒有 JS 時年份按鈕不顯示。
5. **文章列表沒有日期**：`/articles/` 每篇顯示更新日期與署名。

驗證：`python -m pytest` 全綠（覆蓋率 94%）；無頭 Chrome 實測有／無 JavaScript、桌機／手機、以及訪客在 11/27、12/26 來訪時剩餘假日數字會自己更新。改動前的原始碼備份在 `.backup/2026-11-16-pre-review-fixes/`（內含當天的預覽建置 `preview-build-2026-11-16.tgz`）。

注意：`sites/holiday-calendar/public/` 仍是 11-15 的舊輸出，`seoengine deploy` 會先重新建置，不需要手動處理。根目錄的 `_to_delete/` 是測試覆蓋率暫存檔，可直接刪除。

## 尚待使用者決定

- **再部署一次**讓「剩餘假日」引言的小修正上線（`.\.venv\Scripts\seoengine.exe deploy sites/holiday-calendar`）。
- **作者署名**：目前是「Holiday Planner Editorial」（編輯團隊）。審查意見要的是可辨識的作者；若要放真實姓名或筆名，改 `site.yaml` 的 `site.author` 並把 `author_type` 改成 `person`（單篇可用文章 front matter 的 `author:`）。姓名只能由使用者提供。

- `site.contact_email` 已設定為 `hello@asusucloud.com`，但尚未部署；下次正式部署後，Contact 頁才會對外顯示這個地址。

- Google Search Console 網域資源驗證與 sitemap 提交。
- AdSense 的 Privacy & messaging / CMP 設定；不要重送審。

## 重要提醒

- `sites/holiday-calendar/public/` 是可重建輸出，不是手動編輯來源。先前本機 public 曾比線上少 3 篇文章；`content/` 原稿仍齊全。每次要更新必須先重新建置。
- `hc_build.zip` 是 2026-11-11 的較新建置封存，不是側欄 widget 的原始碼。
- 專案自 2026-11-16 起是 Git repository，遠端為 GitHub 私有 repo `peterpitt/seo-money-engine`（分支 `main`）。push 會觸發 `.github/workflows/ci.yml` 跑測試與品質閘門；**自動部署預設關閉**，要設定 Cloudflare Secrets 並把 repo 變數 `AUTO_DEPLOY` 設成 `true` 才會部署。換電腦步驟見 `docs/new-machine-setup.md`。
