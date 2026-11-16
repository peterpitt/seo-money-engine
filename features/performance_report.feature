# language: zh-TW
功能: 成效報告與收益預估
  身為站長
  我想從 Search Console 與收益報表中找出「最快能多賺錢」的優化動作
  以便每週只做投報率最高的事

  場景: 找出排名 8–20 名的擊殺距離關鍵字
    假設 Search Console 匯出資料:
      | query               | clicks | impressions | ctr   | position |
      | 磨豆機推薦          | 40     | 3000        | 1.3%  | 11.2     |
      | 手沖咖啡教學        | 300    | 2000        | 15%   | 2.1      |
      | 磨豆機 刻度         | 2      | 50          | 4%    | 9.0      |
      | best hand grinder   | 5      | 900         | 0.6%  | 14.8     |
    當 我分析擊殺距離關鍵字
    那麼 結果依序應為 "磨豆機推薦, best hand grinder"

  場景: 找出排名不錯但點閱率過低、需要改寫標題的關鍵字
    假設 Search Console 匯出資料:
      | query               | clicks | impressions | ctr   | position |
      | 手沖咖啡教學        | 20     | 2000        | 1%    | 2.0      |
      | 咖啡豆保存          | 280    | 2000        | 14%   | 2.0      |
    當 我分析點閱率落差
    那麼 結果依序應為 "手沖咖啡教學"

  場景: 收益依幣別分開彙總，不混算美金與台幣
    假設 收益明細:
      | date       | page            | source    | amount | currency |
      | 2026-10-01 | /grinder-guide/ | adsense   | 120    | TWD      |
      | 2026-10-01 | /grinder-guide/ | affiliate | 450    | TWD      |
      | 2026-10-02 | /best-grinder/  | amazon    | 18.5   | USD      |
      | 2026-10-03 | /best-grinder/  | adsense   | 3.5    | USD      |
    當 我彙總每頁收益
    那麼 "/grinder-guide/" 的 TWD 收益應為 570
    而且 "/best-grinder/" 的 USD 收益應為 22
    而且 USD 總收益應為 22

  場景: 依目標排名預估雙幣別月收益
    假設 以下關鍵字清單:
      | keyword                      | volume | cpc  | difficulty | market |
      | 手沖咖啡 磨豆機 推薦         | 1900   | 0.9  | 18         | tw     |
      | best hand grinder for travel | 1300   | 1.1  | 12         | us     |
    當 我以目標排名第 3 名預估月收益
    那麼 預估結果應同時有 "TWD" 與 "USD" 兩種幣別
    而且 每個關鍵字的預估點擊應等於搜尋量乘以第 3 名點閱率
