<#
  seoengine 非版控資料備份 -> Google Drive
  備份 git 已排除、硬碟掛了會永久遺失的檔案（憑證 / 抓來的資料 / 個人檔）。
  程式碼本身請用 git push 到 GitHub，不在此備份範圍。
  本腳本會自動偵測 rclone（PATH 找不到會自動安裝），並檢查是否已設定 Google Drive remote。
  首次使用仍需手動跑一次 rclone config 做瀏覽器授權（見 scripts\BACKUP-README.md）。
#>
$ErrorActionPreference = "Stop"

# ===== 設定（可依需要修改）=====
$RepoRoot      = "C:\Users\tt\Downloads\seo-money-engine\seo-money-engine"
$RcloneRemote  = "gdrive"                               # rclone config 建立的 remote 名稱
$DriveFolderId = "1J1zdtLhoey-TKjm4l847skqxkuv9XNFe"    # 目標 Google Drive 資料夾 ID
$Keep          = 14                                     # 雲端保留最近幾份，較舊的自動刪除

# ===== 要備份的項目（git 不保存、不可重建者）=====
$Targets = @(
  "secrets",
  "sites\holiday-calendar\data",
  "存股複利試算_GoogleSheet.xlsx",
  ".backup"
)

# ===== 自動定位 / 安裝 rclone =====
function Resolve-Rclone {
  $cmd = Get-Command rclone -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $shim = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\rclone.exe"
  if (Test-Path $shim) { return $shim }
  $pkg = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Recurse -Filter rclone.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pkg) { return $pkg.FullName }
  Write-Host "  未偵測到 rclone，嘗試用 winget 自動安裝..."
  try { winget install --id Rclone.Rclone -e --accept-source-agreements --accept-package-agreements | Out-Null } catch {}
  $shim = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\rclone.exe"
  if (Test-Path $shim) { return $shim }
  $pkg = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Recurse -Filter rclone.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pkg) { return $pkg.FullName }
  throw "找不到也無法自動安裝 rclone，請手動安裝：https://rclone.org/downloads/"
}

$stamp    = Get-Date -Format "yyyyMMdd-HHmmss"
$stageDir = Join-Path $env:TEMP "seoengine-backup-$stamp"
$zipPath  = Join-Path $env:TEMP "seoengine-backup-$stamp.zip"

Write-Host "=== seoengine 備份 $stamp ==="

# 0) 確認 rclone（沒有就自動裝）
$Rclone = Resolve-Rclone
Write-Host "  rclone: $Rclone"

# 0b) 確認已設定 Google Drive remote
$remotes = & $Rclone listremotes 2>$null
if ($remotes -notcontains "${RcloneRemote}:") {
  Write-Host ""
  Write-Host "[!] rclone 已就緒，但尚未設定名為 '$RcloneRemote' 的 Google Drive remote。"
  Write-Host "    請先手動執行一次（開瀏覽器授權，只需做一次）："
  Write-Host "        rclone config"
  Write-Host "    新增 remote -> 名稱輸入 $RcloneRemote -> 類型選 drive -> auto config 選 y -> 用備份目標的 Google 帳號登入。"
  Write-Host "    設定好後，再跑一次本腳本即可。"
  throw "尚未設定 rclone remote '$RcloneRemote'。"
}

# 1) 收集檔案到暫存區
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
foreach ($t in $Targets) {
  $src = Join-Path $RepoRoot $t
  if (Test-Path $src) {
    $dest = Join-Path $stageDir $t
    New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
    Copy-Item -Path $src -Destination $dest -Recurse -Force
    Write-Host "  [+] $t"
  } else {
    Write-Host "  [-] 略過（不存在）$t"
  }
}

# 2) 壓縮
Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -Force
$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host "  打包完成：$zipPath（$sizeMB MB）"

# 3) 上傳到 Google Drive 指定資料夾
& $Rclone copy $zipPath "${RcloneRemote}:" --drive-root-folder-id $DriveFolderId
if ($LASTEXITCODE -ne 0) { throw "rclone 上傳失敗。" }
Write-Host "  已上傳到 Google Drive 資料夾 $DriveFolderId"

# 4) 清除本機暫存
Remove-Item $stageDir -Recurse -Force
Remove-Item $zipPath -Force

# 5) 僅保留雲端最近 $Keep 份
$all = @(& $Rclone lsf "${RcloneRemote}:" --drive-root-folder-id $DriveFolderId --include "seoengine-backup-*.zip" | Sort-Object)
if ($all.Count -gt $Keep) {
  $all | Select-Object -First ($all.Count - $Keep) | ForEach-Object {
    & $Rclone delete "${RcloneRemote}:$_" --drive-root-folder-id $DriveFolderId
    Write-Host "  清除舊備份：$_"
  }
}

Write-Host "=== 完成 OK ==="
