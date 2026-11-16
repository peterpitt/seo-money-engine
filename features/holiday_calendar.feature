# language: zh-TW
功能: 國定假日行事曆頁面
  身為站長
  我想用一份假日資料檔自動產生行事曆表格、連假攻略與倒數工具
  以便每年只更新資料就能讓「public holidays 2027」這類年年重複的搜尋持續帶來流量

  背景:
    假設 一個新的網站專案，網址為 "https://holidays.example.com"
    而且 專案有日本假日資料，2026 年包含:
      | date       | name                  | local    |
      | 2026-04-29 | Showa Day             | 昭和の日 |
      | 2026-05-03 | Constitution Day      | 憲法記念日 |
      | 2026-05-04 | Greenery Day          | みどりの日 |
      | 2026-05-05 | Children's Day        | こどもの日 |
      | 2026-05-06 | Substitute Holiday    | 振替休日 |

  場景: 行事曆表格自動算出星期幾
    假設 專案中有一篇英文文章 "japan-holidays" 內文含短碼 "[[holidays:jp:2026]]"
    當 我建置網站
    那麼 "japan-holidays/index.html" 應包含 "Wed, Apr 29"
    而且 "japan-holidays/index.html" 應包含 "Showa Day"

  場景: 自動找出連假
    假設 專案中有一篇英文文章 "japan-holidays" 內文含短碼 "[[longweekends:jp:2026]]"
    當 我建置網站
    那麼 "japan-holidays/index.html" 應包含 "Sat, May 2 – Wed, May 6"
    而且 "japan-holidays/index.html" 應包含 "5 days"

  場景: 中文文章使用中文星期
    假設 專案中有一篇中文文章 "japan-holidays-zh" 內文含短碼 "[[holidays:jp:2026]]"
    當 我建置網站
    那麼 "japan-holidays-zh/index.html" 應包含 "4/29（三）"

  場景: 倒數工具內嵌假日資料
    假設 專案中有一篇英文文章 "japan-holidays" 內文含短碼 "[[countdown:jp]]"
    當 我建置網站
    那麼 "japan-holidays/index.html" 應包含 'class="holiday-countdown"'
    而且 "japan-holidays/index.html" 應包含 "2026-05-06"

  場景: 給訪客看的互動假日時間軸頁面
    假設 專案中有一篇英文文章 "holiday-calendar" 內文含短碼 "[[timeline]]"
    當 我建置網站
    那麼 "holiday-calendar/index.html" 應包含 'class="holiday-timeline"'
    而且 "holiday-calendar/index.html" 應包含 '"code": "jp"'
    而且 "holiday-calendar/index.html" 應包含 'src="/timeline.js"'
    而且 應產生檔案 "timeline.js"
    而且 "holiday-calendar/index.html" 不應包含 "revenue"

  場景: 中文時間軸頁面使用中文介面與國名
    假設 專案中有一篇中文文章 "holiday-calendar-zh" 內文含短碼 "[[timeline]]"
    當 我建置網站
    那麼 "holiday-calendar-zh/index.html" 應包含 'data-lang="zh-TW"'
    而且 "holiday-calendar-zh/index.html" 應包含 '"name": "日本"'

  場景: 各國假日統計比較表
    假設 專案中有一篇英文文章 "holiday-calendar" 內文含短碼 "[[holidaystats:2026]]"
    當 我建置網站
    那麼 "holiday-calendar/index.html" 應包含 'class="holiday-table holiday-stats"'
    而且 "holiday-calendar/index.html" 應包含 "Sat, May 2 – Wed, May 6"

  場景: 引用不存在的國家資料時建置失敗
    假設 專案中有一篇英文文章 "bad-calendar" 內文含短碼 "[[holidays:xx:2026]]"
    當 我嘗試建置網站
    那麼 建置應失敗，訊息包含 "xx"

  場景: 「今年剩餘假日」只列出建置當天還沒過的假日
    假設 專案中有一篇英文文章 "japan-holidays" 內文含短碼 "[[remaining:jp:2026]]"
    當 我在 "2026-05-04" 建置網站
    那麼 "japan-holidays/index.html" 應包含 'class="holiday-remaining"'
    而且 "japan-holidays/index.html" 應包含 "Mon, May 4"
    而且 "japan-holidays/index.html" 應包含 "Wed, May 6"
    而且 "japan-holidays/index.html" 不應包含 "Wed, Apr 29"
    而且 "japan-holidays/index.html" 不應包含 "Sun, May 3"
    而且 "japan-holidays/index.html" 應包含 "3 of 5"

  場景: 今年的假日都過完後不再列出表格
    假設 專案中有一篇英文文章 "japan-holidays" 內文含短碼 "[[remaining:jp:2026]]"
    當 我在 "2026-12-01" 建置網站
    那麼 "japan-holidays/index.html" 應包含 "All 2026 holidays have passed"
    而且 "japan-holidays/index.html" 不應包含 "Showa Day"
