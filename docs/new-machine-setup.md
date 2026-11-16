# 換電腦／重新安裝

原始碼在 GitHub 私有 repo：`https://github.com/peterpitt/seo-money-engine`

## 1. 取得程式碼並安裝

```powershell
git clone https://github.com/peterpitt/seo-money-engine.git
cd seo-money-engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS / Linux：source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest                        # 全綠才算裝好
```

`seoengine` 指令裝在 `.venv` 裡。沒啟用虛擬環境時用完整路徑：`.\.venv\Scripts\seoengine.exe ...`

## 2. 部署需要的東西（不在 repo 裡）

- Node.js LTS（`npx wrangler` 用）；第一次部署先 `npx wrangler login` 登入 Cloudflare。
- `secrets/google-ads.yaml`：Google Ads 金鑰，用 `seoengine ads auth` 重新產生或從舊電腦手動複製。**不要放進 repo。**

## 3. 不進版控、換電腦不會跟著走的東西

| 路徑 | 說明 | 怎麼處理 |
|---|---|---|
| `sites/*/public/` | 建置輸出 | `seoengine build` 重新產生 |
| `sites/*/dashboard/` | 站長收益儀表板 | `seoengine viz` 重新產生 |
| `sites/*/data/*.csv`、`trending.json`、`opportunities.json` | Google 匯出與機會資料 | 需要時重新匯入 |
| `.backup/` | 本機備份 | 有需要再手動複製 |
| `secrets/` | 金鑰 | 見上 |

## 4. 日常流程

```powershell
git pull                                             # 開工前
python -m pytest                                     # 改完先測
git add -A; git commit -m "說明"; git push            # 收工
.\.venv\Scripts\seoengine.exe deploy sites/holiday-calendar   # 要上線時（正式部署）
```

push 到 `main` 會觸發 GitHub Actions 跑測試與品質閘門。自動部署預設關閉，開啟方式寫在 `.github/workflows/ci.yml` 開頭。
