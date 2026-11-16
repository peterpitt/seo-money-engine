import datetime as dt
import json

import pytest

from seoengine.calendar import (
    Calendar,
    CalendarError,
    expand_calendar_shortcodes,
    load_calendars,
    long_breaks,
    render_countdown,
    render_holiday_table,
    render_long_breaks,
)

D = dt.date

JP_2027 = {
    "country": "Japan", "country_zh": "日本", "code": "jp", "weekend": ["sat", "sun"],
    "holidays": [
        {"date": "2027-04-29", "name": "Showa Day", "local": "昭和の日"},
        {"date": "2027-05-03", "name": "Constitution Day"},
        {"date": "2027-05-04", "name": "Greenery Day"},
        {"date": "2027-05-05", "name": "Children's Day"},
        {"date": "2027-07-19", "name": "Marine Day"},
    ],
}

AE = {
    "country": "United Arab Emirates", "code": "ae", "weekend": ["sat", "sun"],
    "holidays": [
        {"date": "2026-03-19", "end": "2026-03-22", "name": "Eid Al Fitr holiday", "status": "official"},
        {"date": "2027-03-09", "end": "2027-03-11", "name": "Eid Al Fitr holiday", "status": "estimated"},
        {"date": "2026-08-28", "actual": "2026-08-25", "name": "Prophet's Birthday"},
    ],
}

US = {
    "country": "United States", "code": "us", "weekend": ["sat", "sun"],
    "holidays": [{"date": "2027-07-05", "actual": "2027-07-04", "name": "Independence Day"}],
}


def test_calendar_from_mapping_and_days_off():
    cal = Calendar.from_mapping(AE)
    assert cal.code == "ae"
    assert {D(2026, 3, 19), D(2026, 3, 22)} <= cal.holiday_days(2026)
    assert D(2026, 3, 18) not in cal.holiday_days(2026)


def test_entries_for_year_sorted():
    cal = Calendar.from_mapping(AE)
    assert [e.name for e in cal.entries(2026)] == ["Eid Al Fitr holiday", "Prophet's Birthday"]


@pytest.mark.parametrize("bad", [
    {"code": "Bad Code", "country": "x", "holidays": []},
    {"code": "jp", "country": "x", "weekend": ["funday"], "holidays": []},
    {"code": "jp", "country": "x", "holidays": [{"date": "2027-13-01", "name": "x"}]},
    {"code": "jp", "country": "x", "holidays": [{"date": "2027-01-05", "end": "2027-01-01", "name": "x"}]},
    {"code": "jp", "country": "x", "holidays": [{"date": "2027-01-05", "name": "x", "status": "maybe"}]},
])
def test_calendar_validation(bad):
    with pytest.raises(CalendarError):
        Calendar.from_mapping(bad)


def test_long_breaks_with_bridge_suggestion():
    breaks = long_breaks(Calendar.from_mapping(JP_2027), 2027)
    # 4/29（四）放假、4/30（五）上班、5/1–5/5 連休 → 請 1 天假可以休 7 天
    gw = [b for b in breaks if b.start == D(2027, 4, 29)]
    assert gw and gw[0].end == D(2027, 5, 5) and gw[0].length == 7 and gw[0].leave_days == 1
    natural = [b for b in breaks if b.leave_days == 0]
    assert any(b.start == D(2027, 5, 1) and b.length == 5 for b in natural)
    assert any(b.start == D(2027, 7, 17) and b.length == 3 for b in natural)


def test_low_value_bridges_are_dropped():
    # 8/11（三）山之日：請週一二兩天只換到 5 天（8/7–8/11），效益不足——每請 1 天至少要換到 3 天
    cal = Calendar.from_mapping({"code": "jp", "country": "Japan",
                                 "holidays": [{"date": "2027-08-11", "name": "Mountain Day"}]})
    breaks = long_breaks(cal, 2027)
    assert not any(b.start == D(2027, 8, 7) for b in breaks)
    assert all(b.length >= 3 * b.leave_days for b in breaks)


def test_plain_weekends_are_not_long_breaks():
    breaks = long_breaks(Calendar.from_mapping(JP_2027), 2027)
    assert all(b.holidays for b in breaks)


def test_render_table_english_with_observed_and_range():
    html = render_holiday_table(Calendar.from_mapping(AE), 2026, "en")
    assert "Thu, Mar 19 – Sun, Mar 22" in html
    assert "Fri, Aug 28" in html and "Tue, Aug 25" in html  # 實際日期 vs 放假日


def test_render_table_marks_estimates():
    html = render_holiday_table(Calendar.from_mapping(AE), 2027, "en")
    assert "Expected" in html
    zh = render_holiday_table(Calendar.from_mapping(AE), 2027, "zh-TW")
    assert "預估" in zh and "3/9（二）" in zh


def test_render_table_unknown_year_raises():
    with pytest.raises(CalendarError, match="2030"):
        render_holiday_table(Calendar.from_mapping(US), 2030, "en")


def test_render_long_breaks_table():
    html = render_long_breaks(Calendar.from_mapping(JP_2027), 2027, "en")
    assert "Thu, Apr 29 – Wed, May 5" in html and "7 days" in html and "1 day" in html


def test_countdown_embeds_sorted_json():
    html = render_countdown(Calendar.from_mapping(JP_2027), "en")
    payload = json.loads(html.split("data-holidays='", 1)[1].split("'", 1)[0])
    assert payload[0] == {"date": "2027-04-29", "name": "Showa Day"}
    assert 'data-lang="en"' in html


def test_expand_shortcodes_and_unknown_country():
    cals = {"jp": Calendar.from_mapping(JP_2027)}
    out = expand_calendar_shortcodes("x [[holidays:jp:2027]] y [[countdown:jp]]", cals, "en")
    assert "<table" in out and "holiday-countdown" in out
    with pytest.raises(CalendarError, match="xx"):
        expand_calendar_shortcodes("[[holidays:xx:2027]]", cals, "en")


def test_load_calendars(tmp_path):
    folder = tmp_path / "data" / "holidays"
    folder.mkdir(parents=True)
    (folder / "jp.yaml").write_text(
        "country: Japan\ncode: jp\nholidays:\n  - date: 2027-01-01\n    name: New Year\n", encoding="utf-8"
    )
    assert set(load_calendars(tmp_path)) == {"jp"}
    assert load_calendars(tmp_path / "missing") == {}


def test_code_must_match_filename(tmp_path):
    folder = tmp_path / "data" / "holidays"
    folder.mkdir(parents=True)
    (folder / "jp.yaml").write_text("country: Japan\ncode: us\nholidays: []\n", encoding="utf-8")
    with pytest.raises(CalendarError, match="jp.yaml"):
        load_calendars(tmp_path)


# ---------------------------------------------------------------- 公開時間軸與統計表
from seoengine.calendar import holiday_stats, render_holiday_stats, render_timeline  # noqa: E402

PUBLIC_JP = dict(JP_2027, short="Japan", pages={"en": "/japan-public-holidays/", "zh-TW": "/japan-holidays-zh/"})


def _payload(html):
    raw = html.split('<script type="application/json" class="ht-data">', 1)[1].split("</script>", 1)[0]
    return json.loads(raw)


def test_timeline_payload_english():
    html = render_timeline({"jp": Calendar.from_mapping(PUBLIC_JP)}, None, "en")
    data = _payload(html)
    jp = data["countries"][0]
    assert data["lang"] == "en" and data["years"] == [2027] and data["focus"] == 2027
    assert jp["name"] == "Japan" and jp["page"] == "/japan-public-holidays/"
    assert jp["holidays"][0] == {"start": "2027-04-29", "end": "2027-04-29", "name": "Showa Day",
                                 "local": "昭和の日", "status": "official", "actual": None}
    gw = [b for b in jp["breaks"]["2027"] if b["start"] == "2027-04-29"][0]
    assert gw["leave"] == 1 and gw["length"] == 7
    assert 'src="/timeline.js"' in html and 'data-lang="en"' in html


def test_timeline_payload_chinese_uses_chinese_names_and_page():
    data = _payload(render_timeline({"jp": Calendar.from_mapping(PUBLIC_JP)}, None, "zh-TW"))
    assert data["countries"][0]["name"] == "日本"
    assert data["countries"][0]["page"] == "/japan-holidays-zh/"


def test_timeline_filters_and_orders_codes():
    cals = {"jp": Calendar.from_mapping(PUBLIC_JP), "us": Calendar.from_mapping(US)}
    data = _payload(render_timeline(cals, ["us", "jp"], "en"))
    assert [c["code"] for c in data["countries"]] == ["us", "jp"]
    with pytest.raises(CalendarError, match="xx"):
        render_timeline(cals, ["xx"], "en")


def test_timeline_has_static_fallback_list():
    html = render_timeline({"jp": Calendar.from_mapping(PUBLIC_JP)}, None, "en")
    assert "<noscript>" in html and "Showa Day" in html.split("<noscript>", 1)[1]


def test_timeline_payload_cannot_break_out_of_script():
    bad = dict(PUBLIC_JP, holidays=[{"date": "2027-01-01", "name": "</script><b>x</b>"}])
    html = render_timeline({"jp": Calendar.from_mapping(bad)}, None, "en")
    assert "</script><b>" not in html
    assert _payload(html)["countries"][0]["holidays"][0]["name"] == "</script><b>x</b>"


def test_holiday_stats():
    s = holiday_stats(Calendar.from_mapping(JP_2027), 2027)
    assert s["entries"] == 5 and s["weekday_days"] == 5
    assert (s["longest"].start, s["longest"].length) == (D(2027, 5, 1), 5)
    assert (s["best_bridge"].start, s["best_bridge"].leave_days) == (D(2027, 4, 29), 1)


def test_render_holiday_stats_table():
    html = render_holiday_stats({"jp": Calendar.from_mapping(PUBLIC_JP)}, 2027, "en")
    assert 'class="holiday-table holiday-stats"' in html
    assert '<a href="/japan-public-holidays/">Japan</a>' in html
    assert "Sat, May 1 – Wed, May 5" in html and "Thu, Apr 29 – Wed, May 5" in html


def test_expand_timeline_shortcodes():
    cals = {"jp": Calendar.from_mapping(PUBLIC_JP)}
    out = expand_calendar_shortcodes("[[timeline]]\n\n[[timeline:jp]]\n\n[[holidaystats:2027]]", cals, "en")
    assert out.count('class="holiday-timeline"') == 2 and "holiday-stats" in out


# ---------------------------------------------------------------- 今年剩餘假日（[[remaining:<code>:<year>]]）

def test_remaining_lists_only_holidays_not_yet_over():
    from seoengine.calendar import render_remaining
    html = render_remaining(Calendar.from_mapping(JP_2027), 2027, "en", today=D(2027, 5, 4))
    assert 'class="holiday-remaining"' in html
    assert "Showa Day" not in html and "Constitution Day" not in html      # 4/29、5/3 已過
    assert "Greenery Day" in html and "Children&#x27;s Day" in html and "Marine Day" in html   # 名稱會做 HTML 跳脫
    assert "3 of 5" in html                                                 # 還剩 3 個，全年 5 個
    assert 'data-end="2027-05-04"' in html                                  # 給瀏覽器端每天自動更新用
    assert "as of Tue, May 4, 2027" in html                                 # 靜態文字標明統計日期


def test_remaining_keeps_a_holiday_that_is_still_running_today():
    from seoengine.calendar import render_remaining
    cal = Calendar.from_mapping({"code": "jp", "country": "Japan", "holidays": [
        {"date": "2027-05-03", "end": "2027-05-05", "name": "Golden Week"},
        {"date": "2027-01-01", "name": "New Year's Day"}]})
    html = render_remaining(cal, 2027, "en", today=D(2027, 5, 5))
    assert "Golden Week" in html and "1 of 2" in html


def test_remaining_says_so_when_the_year_is_over():
    from seoengine.calendar import render_remaining
    html = render_remaining(Calendar.from_mapping(JP_2027), 2027, "en", today=D(2027, 12, 1))
    assert "All 2027 holidays have passed" in html
    assert "<table" not in html


def test_remaining_in_chinese():
    from seoengine.calendar import render_remaining
    html = render_remaining(Calendar.from_mapping(JP_2027), 2027, "zh-TW", today=D(2027, 5, 4))
    assert "還沒過的假日" in html and "3 / 5" in html and "5/4（二）" in html
    assert "已全部過完" in render_remaining(Calendar.from_mapping(JP_2027), 2027, "zh-TW", today=D(2028, 1, 1))


def test_remaining_shortcode_uses_the_given_day_and_needs_a_year():
    cals = {"jp": Calendar.from_mapping(JP_2027)}
    out = expand_calendar_shortcodes("[[remaining:jp:2027]]", cals, "en", today=D(2027, 7, 1))
    assert "Marine Day" in out and "Children" not in out and "1 of 5" in out
    with pytest.raises(CalendarError, match="year"):
        expand_calendar_shortcodes("[[remaining:jp]]", cals, "en")
    with pytest.raises(CalendarError, match="2031"):
        expand_calendar_shortcodes("[[remaining:jp:2031]]", cals, "en")
