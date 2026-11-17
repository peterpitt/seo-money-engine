import datetime as dt

import pytest

from seoengine.calendar import Calendar
from seoengine.calendar_page import (
    LANGUAGES,
    CalendarPageConfig,
    fmt_day,
    localized_country,
    localized_holiday,
    page_path,
    render_calendar_page,
)

D = dt.date
I18N = {
    "countries": {"jp": {"ja": "日本", "it": "Giappone", "ar": "اليابان"}},
    "holidays": {"Showa Day": {"it": "Giorno di Shōwa", "ar": "يوم شووا"}, "Golden Week": {"it": "Settimana d'oro"}},
}
JP = Calendar.from_mapping({
    "country": "Japan", "country_zh": "日本", "code": "jp", "language": "ja", "short": "Japan",
    "pages": {"en": "/japan-public-holidays/", "zh-TW": "/japan-holidays-zh/"},
    "holidays": [{"date": "2027-04-29", "name": "Showa Day", "name_zh": "昭和之日", "local": "昭和の日"},
                 {"date": "2027-05-03", "end": "2027-05-05", "name": "Golden Week"},
                 {"date": "2027-12-31", "name": "Extra", "status": "estimated"}],
})


@pytest.mark.parametrize("lang, expected", [
    ("en", "Thu, Apr 29"),
    ("zh-TW", "4/29（四）"),
    ("ja", "4月29日（木）"),
    ("it", "gio 29 apr"),
    ("ar", "الخميس 29 أبريل"),
])
def test_fmt_day(lang, expected):
    assert fmt_day(D(2027, 4, 29), lang) == expected


def test_localized_holiday_prefers_local_language_then_translation_then_english():
    showa = JP.entries(2027)[0]
    assert localized_holiday(showa, JP, "ja", I18N) == "昭和の日"      # 當地語言
    assert localized_holiday(showa, JP, "zh-TW", I18N) == "昭和之日"   # name_zh
    assert localized_holiday(showa, JP, "it", I18N) == "Giorno di Shōwa"
    gw = JP.entries(2027)[1]
    assert localized_holiday(gw, JP, "ar", I18N) == "Golden Week"      # 沒有翻譯就用英文


def test_localized_country():
    assert localized_country(JP, "en", I18N) == "Japan"
    assert localized_country(JP, "zh-TW", I18N) == "日本"
    assert localized_country(JP, "it", I18N) == "Giappone"


def test_page_paths():
    assert page_path("en", "en") == "/"
    assert page_path("zh-TW", "en") == "/calendar/zh-tw/"
    assert page_path("ar", "en") == "/calendar/ar/"
    assert set(LANGUAGES) >= {"en", "zh-TW", "ja", "it", "ar"}


def _render(lang, **kw):
    cfg = CalendarPageConfig(countries=["jp"], languages=["en", "zh-TW", "ja", "it", "ar"], year=2027)
    return render_calendar_page(
        site_name="Holiday Planner", base_url="https://h.example.com", calendars={"jp": JP},
        i18n=I18N, lang=lang, page=cfg, today=kw.get("today", D(2027, 4, 1)))


def test_page_has_tabs_panels_and_rows_with_dates():
    html = _render("en")
    assert 'role="tablist"' in html and 'role="tabpanel"' in html
    assert 'data-date="2027-04-29"' in html
    assert "Thu, Apr 29" in html and "Mon, May 3 – Wed, May 5" in html


def test_estimated_badge_and_long_weekend_chip():
    html = _render("en")
    assert "Expected" in html
    assert "5 days" in html          # 5/1–5/5
    assert "1 leave day" in html     # 4/29–5/5 請 4/30


def test_next_holiday_rendered_from_today():
    html = _render("en", today=D(2027, 4, 30))
    hero = html.split('class="cp-next"', 1)[1].split("</div>", 1)[0]
    assert "Golden Week" in hero and "in 3 days" in hero


def test_language_switcher_and_hreflang():
    html = _render("ja")
    assert '<a href="/" hreflang="en"' in html
    assert 'aria-current="page"' in html
    assert 'hreflang="x-default" href="https://h.example.com/"' in html
    assert '<link rel="canonical" href="https://h.example.com/calendar/ja/">' in html


def test_arabic_page_is_rtl():
    assert '<html lang="ar" dir="rtl">' in _render("ar")


def test_full_guide_links_fall_back_to_english_article():
    assert 'href="/japan-holidays-zh/"' in _render("zh-TW")
    assert 'href="/japan-public-holidays/"' in _render("it")


def test_unknown_language_rejected():
    with pytest.raises(ValueError, match="xx"):
        CalendarPageConfig(countries=["jp"], languages=["en", "xx"], year=2027)


def test_hidden_panels_are_really_hidden():
    """回歸測試：.cp-panel / .cp-year 設了 display:grid，網站 CSS 必須讓 [hidden] 優先，否則切換國家沒有效果。"""
    from seoengine.site import TEMPLATES
    css = (TEMPLATES / "style.css").read_text(encoding="utf-8").replace(" ", "")
    assert "[hidden]{display:none!important" in css


def test_calendar_has_side_rail_and_nonlinked_information_card():
    """側欄提供切換入口；行程資訊是內容提示，不能偽裝成尚未驗證的外部連結。"""
    html = _render("zh-TW")
    assert 'class="cp-rail"' in html
    assert 'class="cp-rail-tab' in html
    assert 'class="cp-spotlight"' in html
    assert "近期假日" in html
    assert "旅遊資訊連結準備中" in html
    assert '<a class="cp-resource-note"' not in html


def test_calendar_footer_links_privacy_in_matching_language():
    assert 'href="/privacy/zh-tw/"' in _render("zh-TW")
    assert 'href="/privacy/"' in _render("ar")


# ---------------------------------------------------------------- 當地時間與時差
import pytest as _pytest

from seoengine.calendar import Calendar as _Calendar, CalendarError as _CalendarError
from seoengine.calendar_page import LANGUAGES as _LANGS, localized_city, utc_label


@_pytest.mark.parametrize("tz, label", [
    ("Asia/Tokyo", "UTC+9"), ("Asia/Dubai", "UTC+4"), ("America/New_York", "UTC−5/−4"),
    ("Europe/Rome", "UTC+1/+2"), ("Asia/Kolkata", "UTC+5:30"), ("UTC", "UTC+0"),
])
def test_utc_label_includes_daylight_saving(tz, label):
    assert utc_label(tz, 2027) == label


def test_calendar_rejects_unknown_timezone():
    with _pytest.raises(_CalendarError, match="timezone"):
        _Calendar.from_mapping({"code": "jp", "timezone": "Asia/Nowhere", "holidays": []})


def test_calendar_timezone_is_optional():
    cal = _Calendar.from_mapping({"code": "jp", "holidays": []})
    assert cal.timezone == ""


def test_localized_city_order():
    cal = _Calendar.from_mapping({"code": "jp", "timezone": "Asia/Tokyo", "city": "Tokyo", "city_zh": "東京",
                                  "holidays": []})
    i18n = {"cities": {"Tokyo": {"ja": "東京", "ar": "طوكيو"}}}
    assert localized_city(cal, "en", i18n) == "Tokyo"
    assert localized_city(cal, "zh-TW", i18n) == "東京"
    assert localized_city(cal, "ar", i18n) == "طوكيو"
    assert localized_city(cal, "it", i18n) == "Tokyo"          # 沒有翻譯時用英文


def test_every_language_has_clock_strings():
    for lang, t in _LANGS.items():
        for key in ("me", "ahead", "behind", "same", "hours"):
            assert t.get(key), (lang, key)
        assert "{h}" in t["ahead"] and "{h}" in t["behind"] and "{n}" in t["hours"]


def test_countries_without_timezone_get_no_clock(tmp_path):
    import datetime as dt

    from seoengine.calendar_page import CalendarPageConfig, render_calendar_page
    cals = {"jp": _Calendar.from_mapping({"code": "jp", "country": "Japan", "timezone": "Asia/Tokyo", "city": "Tokyo",
                                          "holidays": [{"date": "2027-04-29", "name": "Showa Day"}]}),
            "us": _Calendar.from_mapping({"code": "us", "country": "US",
                                          "holidays": [{"date": "2027-07-05", "name": "Independence Day"}]})}
    html = render_calendar_page("S", "https://x.example", cals, {}, "en",
                                CalendarPageConfig(countries=["jp", "us"], languages=["en"], year=2027),
                                today=dt.date(2026, 10, 25))
    jp_tab = html.split('id="tab-jp"', 1)[1].split("</button>", 1)[0]
    us_tab = html.split('id="tab-us"', 1)[1].split("</button>", 1)[0]
    assert "an-clock" in jp_tab and "an-clock" not in us_tab
    jp_panel = html.split('id="panel-jp"', 1)[1].split("</section>", 1)[0]
    us_panel = html.split('id="panel-us"', 1)[1].split("</section>", 1)[0]
    assert 'class="cp-spotlight-clock"' in jp_panel and 'class="cp-spotlight-clock"' not in us_panel


# ---------------------------------------------------------------- 依 UTC 排序
from seoengine.calendar_page import CalendarPageConfig as _Cfg, render_calendar_page as _render_page, standard_offset


@_pytest.mark.parametrize("tz, minutes", [("America/New_York", -300), ("Europe/London", 0), ("Europe/Rome", 60),
                                          ("Asia/Dubai", 240), ("Asia/Tokyo", 540), ("Australia/Sydney", 600),
                                          ("Asia/Kolkata", 330)])
def test_standard_offset_ignores_daylight_saving(tz, minutes):
    assert standard_offset(tz, 2027) == minutes


def _cal(code, tz=None):
    data = {"code": code, "country": code.upper(), "holidays": [{"date": "2027-05-01", "name": "Labour Day"}]}
    if tz:
        data["timezone"] = tz
    return _Calendar.from_mapping(data)


def test_sort_utc_orders_west_to_east_and_keeps_config_order_for_ties():
    import datetime as dt
    import re
    cals = {"jp": _cal("jp", "Asia/Tokyo"), "de": _cal("de", "Europe/Berlin"), "us": _cal("us", "America/New_York"),
            "it": _cal("it", "Europe/Rome"), "xx": _cal("xx")}
    html = _render_page("S", "https://x.example", cals, {}, "en",
                        _Cfg(countries=["jp", "xx", "it", "us", "de"], languages=["en"], year=2027, sort="utc"),
                   today=dt.date(2026, 10, 26))
    assert re.findall(r'id="tab-([a-z]+)"', html) == ["us", "it", "de", "jp", "xx"]   # 沒有時區的放最後
    assert re.search(r'id="tab-us"[^>]*aria-selected="true"', html)                 # 排第一的國家預設選取


def test_default_keeps_config_order():
    assert _Cfg(countries=["jp", "us"]).sort == "config"


def test_unknown_sort_is_rejected():
    with _pytest.raises(ValueError, match="sort"):
        _Cfg(countries=["jp"], sort="random")


def test_sort_is_read_from_site_config():
    assert _Cfg.from_mapping({"countries": ["jp"], "sort": "utc"}).sort == "utc"


@_pytest.mark.parametrize("n, cols", [(9, 3), (8, 4), (6, 3), (4, 4), (2, 2), (1, 1)])
def test_country_grid_picks_columns_without_a_lonely_last_row(n, cols):
    from seoengine.calendar_page import grid_columns
    assert grid_columns(n) == cols


def test_chinese_page_prefers_common_chinese_name_and_keeps_official_name_small():
    from seoengine.calendar import HolidayEntry
    from seoengine.calendar_page import localized_holiday
    import datetime as dt
    tw = _Calendar.from_mapping({"code": "tw", "language": "zh-TW", "holidays": []})
    e = HolidayEntry(start=dt.date(2027, 9, 28), end=dt.date(2027, 9, 28), name="Teachers' Day",
                     name_zh="教師節", local="孔子誕辰紀念日")
    assert localized_holiday(e, tw, "zh-TW", {}) == "教師節"
    jp = _Calendar.from_mapping({"code": "jp", "language": "ja", "holidays": []})
    j = HolidayEntry(start=dt.date(2027, 4, 29), end=dt.date(2027, 4, 29), name="Showa Day", name_zh="昭和之日", local="昭和の日")
    assert localized_holiday(j, jp, "ja", {}) == "昭和の日"          # 日文頁的日本假日仍用當地名稱


# ---------------------------------------------------------------- 多年份：自動選年、隱藏過去年份
def _multi_year_cals():
    hol = lambda y: [{"date": f"{y}-05-01", "name": "Labour Day"}, {"date": f"{y}-12-25", "name": "Christmas Day"}]
    return {"de": _Calendar.from_mapping({"code": "de", "country": "Germany", "timezone": "Europe/Berlin",
                                          "holidays": hol(2026) + hol(2027) + hol(2028) + hol(2029)})}


def _page(today, year="auto", cals=None):
    import datetime as dt
    return _render_page("S", "https://x.example", cals or _multi_year_cals(), {}, "en",
                        _Cfg(countries=["de"], languages=["en"], year=year), today=today)


def test_auto_year_features_next_year_from_october():
    import datetime as dt
    assert "<h1>Public Holidays 2026</h1>" in _page(dt.date(2026, 9, 30))
    assert "<h1>Public Holidays 2027</h1>" in _page(dt.date(2026, 10, 1))
    assert "<h1>Public Holidays 2028</h1>" in _page(dt.date(2027, 12, 31))


def test_auto_year_stays_on_current_year_when_next_year_has_no_data():
    import datetime as dt
    only_2026 = {"de": _Calendar.from_mapping({"code": "de", "country": "Germany",
                                               "holidays": [{"date": "2026-12-25", "name": "Christmas Day"}]})}
    assert "<h1>Public Holidays 2026</h1>" in _page(dt.date(2026, 11, 1), cals=only_2026)


def test_past_years_are_hidden_and_future_years_are_offered():
    import datetime as dt
    import re
    html = _page(dt.date(2027, 1, 5))
    assert re.findall(r'<button type="button" data-year="(\d+)"', html) == ["2027", "2028", "2029"]
    assert 'class="cp-year" data-year="2026"' not in html


def test_fixed_year_is_still_honoured():
    import datetime as dt
    assert "<h1>Public Holidays 2029</h1>" in _page(dt.date(2026, 10, 26), year=2029)


def test_year_setting_accepts_auto_and_rejects_nonsense():
    assert _Cfg.from_mapping({"countries": ["de"], "year": "auto"}).year == "auto"
    with _pytest.raises(ValueError, match="year"):
        _Cfg.from_mapping({"countries": ["de"], "year": "next"})


# ---------------------------------------------------------------- 審核修正：靜態內容與預設年份

def test_every_country_panel_is_in_the_static_html_without_hidden():
    """沒有 JavaScript（或只讀靜態 HTML 的爬蟲）也要看得到每個國家的假日。"""
    import re
    html = _render_page("S", "https://x.example", {"jp": JP, **_multi_year_cals()}, I18N, "en",
                        _Cfg(countries=["jp", "de"], languages=["en"], year=2027), today=D(2026, 11, 16))
    tags = re.findall(r'<section class="cp-panel[^>]*>', html)
    assert len(tags) == 2
    assert all(" hidden" not in t for t in tags)
    assert 'classList.add("cp-js")' in html.split("</head>", 1)[0]     # 有 JS 才收合成分頁，避免閃爍


def test_css_collapses_inactive_panels_only_when_js_is_on():
    from seoengine.site import TEMPLATES
    css = (TEMPLATES / "style.css").read_text(encoding="utf-8").replace(" ", "")
    assert ".cp-js.cp-panel:not(.is-in){display:none" in css
    assert "html:not(.cp-js).cp-years{display:none" in css             # 沒有 JS 時年份按鈕按了沒反應，不顯示


def test_default_year_block_comes_first_and_buttons_stay_chronological():
    """標題寫 2027 時，靜態 HTML 裡 2027 的假日要排在 2026 之前。"""
    import datetime as dt
    import re
    html = _page(dt.date(2026, 11, 16))
    assert "<h1>Public Holidays 2027</h1>" in html
    assert re.findall(r'<div class="cp-year" data-year="(\d+)"', html)[:2] == ["2027", "2026"]
    assert re.findall(r'<button type="button" data-year="(\d+)"', html)[:2] == ["2026", "2027"]
    assert '<div class="cp-year" data-year="2026" hidden>' in html     # 其他年份仍然預設收起來


# ---------------------------------------------------------------- 桌機聚光燈卡的當地時鐘
def test_desktop_spotlight_has_local_clock_for_countries_with_timezone():
    import datetime as dt
    html = _page(dt.date(2026, 11, 17))                    # de：Europe/Berlin
    head = html.split('class="cp-spotlight-head"', 1)[1].split('class="cp-spotlight-next"', 1)[0]
    assert 'class="cp-spotlight-clock" data-tz="Europe/Berlin"' in head
    for part in ("an-h", "an-m", "an-s", "an-ampm", "cp-clock-time"):
        assert f'class="{part}"' in head, part
    assert ".cp-spotlight-clock[data-tz]" in html          # 時鐘 JS 也要驅動聚光燈時鐘


def test_spotlight_clock_hidden_on_mobile_to_avoid_duplicate_with_tab_clock():
    from seoengine.site import TEMPLATES
    css = (TEMPLATES / "style.css").read_text(encoding="utf-8").replace(" ", "")
    assert ".cp-spotlight-clock{display:none" in css       # 手機版隱藏，不跟 tab 卡片時鐘重複
    assert ".cp-spotlight-head>span:first-child{" in css   # 國碼徽章規則只套第一個子元素，別把時鐘 span 變成圓框


# ---------------------------------------------------------------- 資產快取破壞（避免新 HTML 配到舊 CSS）
def test_calendar_stylesheet_link_is_cache_busted():
    import re
    html = _render("en")
    m = re.search(r'<link rel="stylesheet" href="/style\.css\?v=([0-9a-f]{6,})">', html)
    assert m, "行事曆頁的 style.css 連結要帶內容版本號"
