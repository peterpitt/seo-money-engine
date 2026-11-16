# 備份設定（一次性）

`backup-to-gdrive.ps1` 會把 git 不保存、硬碟掛了會永久遺失的檔案
（`secrets/`、抓來的關鍵字/趨勢資料、個人 xlsx、`.backup/`）打包上傳到 Google Drive。
**程式碼本身請用 `git push` 到 GitHub，不在此備份範圍。**

## 1. 安裝 rclone
到 https://rclone.org/downloads/ 下載 Windows 版，解壓後把 `rclone.exe` 放進 PATH，
或在 `backup-to-gdrive.ps1` 把 `$Rclone` 改成 `rclone.exe` 的完整路徑。

## 2. 設定 Google Drive remote（一次就好，會開瀏覽器授權）
    rclone config
  - `n`（新 remote）
  - name 輸入：`gdrive`
  - storage 選：`drive`（Google Drive）
  - client_id / client_secret：直接 Enter 留空
  - scope：選 `1`（drive 完整）
  - root_folder_id / service account：直接 Enter 留空
  - Edit advanced config：`n`
  - Use auto config：`y`（開瀏覽器，用你要備份去的那個 Google 帳號登入授權）
  - 確認 `y` → `q` 離開

## 3. 手動跑一次測試
    powershell -ExecutionPolicy Bypass -File ".\scripts\backup-to-gdrive.ps1"
  跑完去那個 Google Drive 資料夾看有沒有 `seoengine-backup-*.zip`。

## 4. 排程（每週日 03:00 自動備份）
    schtasks /create /tn "seoengine-backup" /sc weekly /d SUN /st 03:00 /tr "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\tt\Downloads\seo-money-engine\seo-money-engine\scripts\backup-to-gdrive.ps1\""

  頻率可改：`/sc daily`（每天）、`/sc weekly`（每週）。
