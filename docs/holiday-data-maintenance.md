# 假日資料年度維護

資料在 `sites/holiday-calendar/data/holidays/<國碼>.yaml`。目前收錄 2026–2029。

## 網站會自動處理的事（不用手動改）

- **預設顯示哪一年**：`site.yaml` 的 `calendar_page.year: auto`。1–9 月顯示今年，**10 月起顯示明年**（「明年連假」的搜尋從秋天開始變多）。
- **過去的年份**：自動隱藏，例如 2027 年 1 月起不再顯示 2026。
- **國家順序**：`sort: utc`，依標準時區由西到東，新增國家自動排好。
- **倒數天數**：瀏覽器端即時計算；GitHub Actions 每週一自動重建一次，讓頁面上的文字與預設年份保持最新。
- **儀表板「待官方公告的假日」**：只列未來約 13 個月內的預估日期，更遠的只顯示數量。

## 什麼時候要更新資料

`status: estimated` 是預估日期，頁面會標「預估」。官方公布後把日期改成正確的、刪掉 `status: estimated`（或改成 `official`）。

| 國家 | 誰公布 | 大約什麼時候 | 要做的事 |
|---|---|---|---|
| 台灣 | 人事行政總處「政府行政機關辦公日曆表」 | **前一年 6 月左右** | 核對整年日期、補假；全部改 official |
| 日本 | 內閣府（春分・秋分由國立天文台在官報公告） | **前一年 2 月初** | 只改春分、秋分與其補假 |
| 阿聯 | 內閣／人力資源部 | **每個伊斯蘭節日前幾天** | 開齋節、宰牲節、伊斯蘭新年、先知誕辰改成公告日期 |
| 英國 | GOV.UK（bank-holidays） | 約提前一年半 | 2029 公布後改 official |
| 美國、德國、法國、義大利、澳洲（NSW） | 法律規則固定 | 不需公告 | 只要加新年度；臨時加放的假日（例如國喪）再補 |

## 新增一個年度（例如 2030）

1. 用 python-holidays 產生參考清單（只當參考，不直接採用）：

   ```bash
   pip install holidays
   python -c "import holidays; [print(d, d.strftime('%a'), n) for d, n in sorted(holidays.country_holidays('JP', years=2030, language='en_US').items())]"
   ```

   英國用 `subdiv='ENG'`、澳洲用 `subdiv='NSW'`。

2. 照同一個檔案裡前一年的寫法新增：沿用相同的 `name`（翻譯靠它對應）、`name_zh`、`local`。
3. **補假的寫法**：`date` 是實際放假日，`actual` 是原本的日期（例如英國聖誕節逢週六：`date: 2030-12-27, actual: 2030-12-25`）。
4. **跨年補假**：隔年元旦逢週六而提前到 12/31 放的，列在前一年，隔年不要再列 1/1（美國、台灣都有這種情況）。
5. **刻意不列的日子**：義大利 11 月第一個週日的國家統一日（只是紀念，不放假）、澳洲 8 月的 Bank Holiday（只有銀行休息）。python-holidays 會列出它們，比對時忽略。
6. 還沒官方公布的，加上 `status: estimated`。
7. 跑測試與建置：

   ```bash
   python -m pytest tests/unit/test_site_holiday_data.py
   seoengine build sites/holiday-calendar
   ```

   `test_site_holiday_data.py` 會檢查每個假日都有中、日、義、阿拉伯文名稱。新名稱要補到 `i18n.yaml`。
