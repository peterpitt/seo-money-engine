# language: zh-TW
功能: 關鍵字金礦評估
  身為一個靠 SEO 變現的站長
  我想要自動判斷搜尋意圖並依「錢景」排序關鍵字
  以便把有限的寫作時間花在最可能賺錢的主題上

  場景大綱: 依關鍵字判斷搜尋意圖
    假設 關鍵字 "<關鍵字>"
    當 系統判斷搜尋意圖
    那麼 搜尋意圖應為 "<意圖>"

    例子:
      | 關鍵字                          | 意圖          |
      | 手沖咖啡 磨豆機 推薦            | commercial    |
      | best coffee grinder 2026        | commercial    |
      | baratza encore vs timemore c3   | commercial    |
      | 磨豆機 優惠 折扣碼              | transactional |
      | buy burr grinder coupon         | transactional |
      | 磨豆機 如何 清潔                | informational |
      | how to clean a burr grinder     | informational |
      | amazon login                    | navigational  |

  場景: 高單價、低難度的商業型關鍵字排在最前面
    假設 以下關鍵字清單:
      | keyword                   | volume | cpc  | difficulty | market |
      | 咖啡 歷史                 | 9000   | 0.1  | 20         | tw     |
      | 手沖咖啡 磨豆機 推薦      | 1900   | 0.6  | 18         | tw     |
      | best coffee grinder       | 40000  | 1.2  | 85         | us     |
      | best hand grinder for travel | 1600 | 1.1 | 12        | us     |
    當 我依錢景分數排序
    那麼 第一名應為 "best hand grinder for travel"
    而且 "咖啡 歷史" 的排名應在 "手沖咖啡 磨豆機 推薦" 之後

  場景: 過濾掉新站打不贏的高難度關鍵字
    假設 以下關鍵字清單:
      | keyword                   | volume | cpc  | difficulty | market |
      | best coffee grinder       | 40000  | 1.2  | 85         | us     |
      | best hand grinder for travel | 1300 | 1.1 | 12        | us     |
    當 我以難度上限 40 排序
    那麼 結果應只包含 "best hand grinder for travel"

  場景: 相近的關鍵字被歸入同一個主題群
    假設 以下關鍵字清單:
      | keyword                         | volume | cpc  | difficulty | market |
      | best coffee grinder             | 5000   | 1.2  | 30         | us     |
      | best coffee grinder under 100   | 900    | 1.4  | 20         | us     |
      | how to descale espresso machine | 2400   | 0.4  | 15         | us     |
    當 我將關鍵字分群
    那麼 應產生 2 個主題群
    而且 "best coffee grinder" 與 "best coffee grinder under 100" 應在同一群

  場景: 直接匯入 Google Ads 關鍵字規劃工具的匯出檔
    假設 一個 Google Ads 匯出檔（UTF-16、Tab 分隔、台幣出價）:
      | 关键字     | 货币 | 平均每月搜索量 | 竞争 | 页首出价（低位区间） | 页首出价（高位区间） |
      | 日本黃金週 | TWD  | 1万 – 10万     | 低   | 0.42                 | 4.34                 |
      | 日本 3 連休 | TWD | --             |      |                      |                      |
    當 我用匯率 TWD=0.0307 匯入
    那麼 應匯入 1 個關鍵字
    而且 "日本黃金週" 的市場應為 "tw"、搜尋量約 31623
