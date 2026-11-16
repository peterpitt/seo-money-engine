# language: zh-TW
功能: 隱私權政策頁
  身為站長
  我需要一份符合 AdSense 規定的隱私權政策，並從每一頁的頁尾都連得到
  以便通過 AdSense 審核，也讓訪客知道網站用了哪些 cookie

  背景:
    假設 一個網站專案，網址為 "https://asusucloud.site"，啟用 AdSense 與 GA4

  場景: 英文與中文隱私權政策都會產生
    當 我建置網站
    那麼 應產生檔案 "privacy/index.html"
    而且 應產生檔案 "privacy/zh-tw/index.html"
    而且 "sitemap.xml" 應包含 "https://asusucloud.site/privacy/"

  場景: 隱私權政策包含 AdSense 規定的揭露
    當 我建置網站
    那麼 "privacy/index.html" 應包含 "Third-party vendors, including Google, use cookies"
    而且 "privacy/index.html" 應包含 "https://www.google.com/settings/ads"
    而且 "privacy/index.html" 應包含 "https://www.aboutads.info/choices/"
    而且 "privacy/index.html" 應包含 "Google Analytics"
    而且 "privacy/index.html" 應包含 "affiliate"

  場景: 每一頁頁尾都連到同語言的隱私權政策
    當 我建置網站
    那麼 "a/index.html" 應包含 'href="/privacy/zh-tw/"'
    而且 "privacy/index.html" 應包含 'href="/privacy/"'

  場景: 網站會產生完整的信任資訊頁
    當 我建置網站
    那麼 應產生檔案 "about/index.html"
    而且 應產生檔案 "about/zh-tw/index.html"
    而且 應產生檔案 "contact/index.html"
    而且 應產生檔案 "terms/index.html"
    而且 "sitemap.xml" 應包含 "https://asusucloud.site/about/"
    而且 "sitemap.xml" 應包含 "https://asusucloud.site/contact/"
    而且 "sitemap.xml" 應包含 "https://asusucloud.site/terms/"

  場景: 每一頁頁尾都連到所有信任資訊頁
    當 我建置網站
    那麼 "a/index.html" 應包含 'href="/about/zh-tw/"'
    而且 "a/index.html" 應包含 'href="/contact/zh-tw/"'
    而且 "a/index.html" 應包含 'href="/terms/zh-tw/"'

  場景: 文章署名連到關於我們頁面
    當 我建置網站
    那麼 "a/index.html" 應包含 'rel="author" href="/about/zh-tw/"'
