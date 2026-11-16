# language: zh-TW
功能: 串接 Google Trends 與 Google Ads 找出能變現的流量
  身為站長
  我想用 Google Trends 看出大家正在搜什麼、什麼時候是旺季，用 Google Ads Keyword Planner 拿到真實的搜尋量與出價
  以便把寫作時間花在「有人搜、有人出價、正在升溫」的主題上

  場景: 從 Google Trends 熱門 RSS 找出跟網站主題相關的熱搜
    假設 Google Trends 美國熱門 RSS 有以下熱搜:
      | title                          | traffic |
      | patriots vs bears              | 1M+     |
      | public holidays in the uae     | 20K+    |
      | thanksgiving long weekend 2027 | 5K+     |
    當 我以主題 "holiday,long weekend" 篩選熱搜
    那麼 篩選結果依序應為 "public holidays in the uae, thanksgiving long weekend 2027"
    而且 "public holidays in the uae" 的流量應為 20000

  場景: 匯入 Google Trends 匯出的 CSV，算出旺季與最晚發布日
    假設 今天是 "2026-10-24"
    而且 一份 Google Trends 匯出 CSV，關鍵字 "public holidays" 每年 1 月最高
    當 我分析季節性
    那麼 旺季月份應為 1
    而且 建議最晚發布日應為 "2026-11-20"

  場景: 用 Keyword Planner 的真實數據更新關鍵字檔
    假設 Google Ads 帳戶幣別為 "TWD"，匯率設定 1 TWD = 0.031 USD
    而且 Keyword Planner 對種子 "public holidays 2027" 回傳:
      | text                        | avg_monthly_searches | competition_index | low_bid_micros | high_bid_micros |
      | public holidays 2027        | 22200                | 35                | 8000000        | 24000000        |
      | federal holidays 2027 list  | 8100                 | 20                | 6000000        | 16000000        |
    當 我用市場 "us" 產生關鍵字檔
    那麼 關鍵字 "public holidays 2027" 的搜尋量應為 22200
    而且 關鍵字 "public holidays 2027" 的 CPC 應約為 0.496 美元
    而且 關鍵字 "public holidays 2027" 的難度應為 35
    而且 關鍵字檔應標示資料來源為 "google-ads"

  場景: 帳戶幣別不是美元又沒設定匯率時拒絕寫入
    假設 Google Ads 帳戶幣別為 "TWD"，沒有設定匯率
    而且 Keyword Planner 對種子 "public holidays 2027" 回傳:
      | text                 | avg_monthly_searches | competition_index | low_bid_micros | high_bid_micros |
      | public holidays 2027 | 22200                | 35                | 8000000        | 24000000        |
    當 我嘗試用市場 "us" 產生關鍵字檔
    那麼 應出現錯誤，訊息包含 "fx_to_usd"

  場景: 合併三種資料排出流量機會，已經寫過的主題不重複
    假設 一個新的網站專案，網址為 "https://holidays.example.com"
    而且 專案已有一篇文章，關鍵字為 "federal holidays 2027"
    而且 專案的關鍵字檔來自 Google Ads:
      | keyword                     | volume | cpc  | difficulty | market |
      | federal holidays 2027       | 22000  | 0.45 | 42         | us     |
      | uae public holidays 2027    | 6000   | 0.55 | 18         | us     |
      | golden week 2027 dates      | 1800   | 0.60 | 12         | us     |
    而且 熱搜中有 "uae public holidays"
    當 我計算流量機會並為前 1 名產生文章骨架
    那麼 第一名應為 "uae public holidays 2027"，並標示為熱搜中
    而且 "federal holidays 2027" 應標示已有文章
    而且 應產生草稿 "uae-public-holidays-2027.md"

  場景: 官方 Google Trends API 尚未開通時給出清楚說明
    當 我呼叫官方 Google Trends API
    那麼 應出現錯誤，訊息包含 "alpha"
