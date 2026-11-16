# language: zh-TW
功能: 給訪客的多語言假日行事曆
  身為訪客
  我想點一下國家就看到下一個假日、全年假日與連假，而且用我看得懂的語言
  以便不用讀長文章就能安排休假與旅行

  背景:
    假設 一個新的網站專案，網址為 "https://holidays.example.com"
    而且 專案有日本與美國的 2027 假日資料
    而且 網站設定行事曆頁面，國家為 "jp,us"，語言為 "en,zh-TW,ja,ar"

  場景: 每個語言都產生獨立的行事曆頁面
    當 我建置網站
    那麼 應產生檔案 "index.html"
    而且 應產生檔案 "_redirects"
    而且 "_redirects" 應包含 "/calendar/ /"
    而且 應產生檔案 "calendar/zh-tw/index.html"
    而且 應產生檔案 "calendar/ja/index.html"
    而且 應產生檔案 "calendar/ar/index.html"
    而且 "sitemap.xml" 應包含 "https://holidays.example.com/calendar/ja/"
    而且 "index.html" 應包含 'hreflang="ja" href="https://holidays.example.com/calendar/ja/"'

  場景: 用區塊切換國家
    當 我建置網站
    那麼 "index.html" 應包含 'role="tablist"'
    而且 "index.html" 應包含 'id="tab-jp"'
    而且 "index.html" 應包含 'id="tab-us"'

  場景: 日文頁面用日文日期與日本當地的假日名稱
    當 我建置網站
    那麼 "calendar/ja/index.html" 應包含 "4月29日（木）"
    而且 "calendar/ja/index.html" 應包含 "昭和の日"
    而且 "calendar/ja/index.html" 應包含 "独立記念日"

  場景: 阿拉伯文頁面由右至左排版
    當 我建置網站
    那麼 "calendar/ar/index.html" 應包含 '<html lang="ar" dir="rtl">'

  場景: 訪客頁面保持簡潔，不放長篇文字也不含收益資訊
    當 我建置網站
    那麼 行事曆頁面的段落文字應少於 40 字
    而且 "index.html" 不應包含 "revenue"

  場景: 每個國家卡片同時顯示當地時間、跟訪客的時差，以及下一個假日倒數
    當 我建置網站
    那麼 每個國家只有一張卡片，當地時間就在那張卡片裡
    而且 "calendar/zh-tw/index.html" 應包含 'data-tz="Asia/Tokyo"'
    而且 "calendar/zh-tw/index.html" 應包含 "東京"
    而且 "calendar/zh-tw/index.html" 應包含 "UTC+9"
    而且 "calendar/zh-tw/index.html" 應包含 "你的時間"
    而且 "index.html" 應包含 "New York"
    而且 "index.html" 應包含 "UTC−5/−4"
    而且 "calendar/ja/index.html" 應包含 "ニューヨーク"

  場景: 每個國家卡片右上角有當地時間的指針時鐘，標示上午或下午
    當 我建置網站
    那麼 每張國家卡片都應有指針時鐘，含時針、分針、秒針與上午／下午
    而且 頁首不應有時鐘

  場景: 大螢幕可用側邊節慶倒數切換國家，並顯示不含外連結的行程資訊
    當 我建置網站
    那麼 "calendar/zh-tw/index.html" 應包含 'class="cp-rail"'
    而且 "calendar/zh-tw/index.html" 應包含 'class="cp-rail-tab'
    而且 "calendar/zh-tw/index.html" 應包含 'class="cp-spotlight"'
    而且 "calendar/zh-tw/index.html" 應包含 "近期假日"
    而且 "calendar/zh-tw/index.html" 應包含 "旅遊資訊連結準備中"

  場景: 國家卡片依 UTC 時區由西到東排列
    假設 行事曆設定依 UTC 時區排序
    當 我建置網站
    那麼 國家卡片的順序應為 "us,jp"

  場景: 不執行 JavaScript 也看得到每個國家的假日
    當 我建置網站
    那麼 每個國家的假日面板在靜態頁面都看得到
    而且 "index.html" 應包含 "Showa Day"
    而且 "index.html" 應包含 "Independence Day"

  場景: 標題年份的假日排在其他年份之前
    假設 美國另有 2026 年的假日資料
    當 我建置網站
    那麼 "index.html" 應包含 "<h1>Public Holidays 2027</h1>"
    而且 每個國家面板的第一個年份區塊都是 2027
