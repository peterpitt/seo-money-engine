# language: zh-TW
功能: 變現元件
  身為站長
  我想在 Markdown 裡用短碼插入聯盟連結、CTA 與比較表，並自動排入 AdSense 版位
  以便寫作時專心在內容，變現細節由系統處理且符合 Google 規範

  背景:
    假設 已登記聯盟商品 "h1" 名稱為 "Brewlab H1 手搖磨豆機" 連結為 "https://aff.brewlab.tw/h1?ref=me"

  場景: 聯盟短碼轉為帶 sponsored 屬性的跳轉連結
    當 我展開短碼 "想入手可以看 [[offer:h1]] 的價格"
    那麼 輸出應包含 'href="/go/h1/"'
    而且 輸出應包含 'rel="sponsored nofollow noopener"'
    而且 輸出不應包含 "aff.brewlab.tw"
    而且 使用到的商品應為 "h1"

  場景: 引用不存在的商品時建置失敗
    當 我展開短碼 "[[offer:ghost]]"
    那麼 應拋出變現錯誤，訊息包含 "ghost"

  場景: 跳轉頁不被索引並導向真實聯盟網址
    當 我產生 "h1" 的跳轉頁
    那麼 輸出應包含 'name="robots" content="noindex, nofollow"'
    而且 輸出應包含 "https://aff.brewlab.tw/h1?ref=me"

  場景: 廣告數量不超過上限且間隔足夠字數
    假設 AdSense 設定 client 為 "ca-pub-1234567890" 上限 2 則、間隔 50 字
    而且 一段有 5 個 H2 段落、每段 60 字的文章 HTML
    當 我插入廣告版位
    那麼 應插入 2 個 AdSense 廣告單元
    而且 每個廣告前都有高轉換版位註記

  場景: 尚未設定 AdSense 時不輸出任何廣告碼
    假設 AdSense 設定 client 為 "" 上限 3 則、間隔 50 字
    而且 一段有 5 個 H2 段落、每段 60 字的文章 HTML
    當 我插入廣告版位
    那麼 應插入 0 個 AdSense 廣告單元
    而且 輸出不應包含 "adsbygoogle"

  場景: 連結還是範例網址的聯盟商品不會出現在網站上
    假設 已登記聯盟商品 "demo" 名稱為 "示範訂房" 連結為 "https://example.com/aff/demo"
    當 我展開短碼 "訂房前先比價 [[offer:demo]]。[[cta:demo]][[compare:demo]]"
    那麼 輸出不應包含 "/go/demo/"
    而且 輸出應包含 "訂房前先比價 示範訂房。"
    而且 沒有使用到任何商品
