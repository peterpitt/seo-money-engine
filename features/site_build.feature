# language: zh-TW
功能: 靜態網站建置
  身為站長
  我想一個指令就產生可直接部署、SEO 結構完整的靜態網站
  以便免伺服器成本上線，並讓 Google 正確索引與顯示複合式搜尋結果

  背景:
    假設 一個新的網站專案，網址為 "https://coffee.example.com"
    而且 已登記聯盟商品 "h1" 名稱為 "Brewlab H1 手搖磨豆機" 連結為 "https://aff.brewlab.tw/h1?ref=me"

  場景: 合格文章被發布並產生 SEO 必備檔案
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"
    當 我建置網站
    那麼 應產生檔案 "grinder-guide/index.html"
    而且 應產生檔案 "sitemap.xml"
    而且 應產生檔案 "robots.txt"
    而且 應產生檔案 "feed.xml"
    而且 "sitemap.xml" 應包含 "https://coffee.example.com/grinder-guide/"
    而且 "robots.txt" 應包含 "Disallow: /go/"
    而且 "grinder-guide/index.html" 應包含 '<link rel="canonical" href="https://coffee.example.com/grinder-guide/">'
    而且 "grinder-guide/index.html" 應包含 '"@type": "Article"'

  場景: 有常見問答時輸出 FAQPage 結構化資料
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"，並附 2 則常見問答
    當 我建置網站
    那麼 "grinder-guide/index.html" 應包含 '"@type": "FAQPage"'

  場景: 未通過品質閘門的文章不會被發布
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"
    而且 專案中有一篇含 AI 套話的文章 "bad-post"
    當 我建置網站
    那麼 不應產生檔案 "bad-post/index.html"
    而且 "sitemap.xml" 不應包含 "bad-post"
    而且 建置結果應記錄 "bad-post" 因品質閘門被略過

  場景: 草稿不會被發布
    假設 專案中有一篇草稿 "secret-draft"
    當 我建置網站
    那麼 不應產生檔案 "secret-draft/index.html"

  場景: 使用聯盟連結的文章自動加上揭露聲明並產生跳轉頁
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"，內文引用商品 "h1"
    當 我建置網站
    那麼 應產生檔案 "go/h1/index.html"
    而且 "grinder-guide/index.html" 應包含 "affiliate-disclosure"

  場景: 文章之間自動建立內部連結
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"
    而且 專案中有一篇合格文章 "pour-over" 關鍵字為 "手沖咖啡教學"，內文提到 "磨豆機推薦"
    當 我建置網站
    那麼 "pour-over/index.html" 應包含 'href="/grinder-guide/"'

  場景: 中英雙語版本互相宣告 hreflang
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"，翻譯群組為 "grinder"
    而且 專案中有一篇英文合格文章 "best-grinder" 關鍵字為 "best coffee grinder"，翻譯群組為 "grinder"
    當 我建置網站
    那麼 "grinder-guide/index.html" 應包含 'hreflang="en" href="https://coffee.example.com/best-grinder/"'
    而且 "best-grinder/index.html" 應包含 'hreflang="zh-TW" href="https://coffee.example.com/grinder-guide/"'

  場景: 設定 AdSense 後產生 ads.txt
    假設 AdSense 發布商 ID 為 "ca-pub-1234567890"
    而且 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"
    當 我建置網站
    那麼 "ads.txt" 應包含 "google.com, pub-1234567890, DIRECT, f08c47fec0942fa0"

  場景: 文章列表顯示每篇文章的更新日期與作者
    假設 專案中有一篇合格文章 "grinder-guide" 關鍵字為 "磨豆機推薦"
    當 我建置網站
    那麼 文章列表的每一篇都應顯示日期與作者
    而且 "index.html" 應包含 '<time datetime="2026-10-01">'
