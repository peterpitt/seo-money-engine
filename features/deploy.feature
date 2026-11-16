# language: zh-TW
功能: 部署到 Cloudflare Pages
  身為站長
  我想一個指令就把前端網站部署到自己的網域，而且絕不把收益儀表板或金鑰傳上去
  以便安心上線，網址正確，Google 才會正確收錄

  背景:
    假設 一個網站專案，網址為 "https://asusucloud.site"，Cloudflare Pages 專案為 "asusucloud"

  場景: 建置結果帶有 Cloudflare 標頭設定
    當 我建置網站
    那麼 應產生檔案 "_headers"
    而且 "_headers" 應包含 "X-Content-Type-Options: nosniff"
    而且 "_headers" 應包含 "/style.css"

  場景: 部署指令只上傳前端資料夾
    假設 專案裡有收益儀表板與 Google 金鑰
    當 我部署網站
    那麼 應執行 wrangler 部署 "public" 資料夾到專案 "asusucloud"
    而且 上傳的資料夾不應包含儀表板或金鑰

  場景: 網址還是範例網域時拒絕部署
    假設 網站網址改成 "https://holidays.example.com"
    當 我部署網站
    那麼 部署應被拒絕，訊息包含 "base_url"
