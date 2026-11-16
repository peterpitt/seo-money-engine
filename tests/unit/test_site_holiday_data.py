"""假日網站的真實資料：日期對照官方來源，翻譯不可缺漏。

來源（2026-10-26 查核）：
- 英國：GOV.UK bank-holidays.json（England and Wales）
- 澳洲：nsw.gov.au/about-nsw/public-holidays（新南威爾斯州，雪梨）
- 法國：WEKA、calendriergratuit.fr 的 2027 jours fériés（11 天）
- 德國：kalenderpedia.de bundesweite Feiertage（9 天）
- 台灣：人事行政總處 115、116 年辦公日曆表（104 人力銀行整理、ETtoday 2026-05-21 報導），
  python-holidays 0.107 交叉比對；已無補行上班日
"""
import datetime as dt
from pathlib import Path

import pytest
import yaml

from seoengine.calendar import _COUNTRY_COLORS, load_calendars
from seoengine.calendar_page import load_i18n

PROJECT = Path(__file__).parents[2] / "sites" / "holiday-calendar"
COUNTRIES = ["us", "ae", "it", "jp", "de", "fr", "gb", "au", "tw"]
D = dt.date


@pytest.fixture(scope="module")
def cals():
    return load_calendars(PROJECT)


@pytest.fixture(scope="module")
def i18n():
    return load_i18n(PROJECT)


def _on(cal, day):
    return next((e for e in cal.entries_all if e.start == day), None)


def test_site_shows_all_countries():
    config = yaml.safe_load((PROJECT / "site.yaml").read_text(encoding="utf-8"))
    assert config["calendar_page"]["countries"] == COUNTRIES


def test_every_country_has_data_timezone_city_and_its_own_color(cals):
    assert set(COUNTRIES) <= set(cals)
    for code in COUNTRIES:
        cal = cals[code]
        assert cal.timezone and cal.city and cal.city_zh and cal.country_zh, code
        assert {2026, 2027} <= cal.years(), code
    colors = [_COUNTRY_COLORS[c] for c in COUNTRIES]
    assert len(set(colors)) == len(colors)


@pytest.mark.parametrize("code, year, count", [("de", 2026, 9), ("de", 2027, 9), ("fr", 2026, 11), ("fr", 2027, 11),
                                               ("gb", 2026, 8), ("gb", 2027, 8), ("au", 2026, 12), ("au", 2027, 12),
                                               ("tw", 2026, 12), ("tw", 2027, 13)])
def test_holiday_counts_match_official_lists(cals, code, year, count):
    assert len(cals[code].entries(year)) == count


@pytest.mark.parametrize("code, day, local", [
    ("de", D(2027, 3, 26), "Karfreitag"), ("de", D(2027, 5, 6), "Christi Himmelfahrt"),
    ("de", D(2027, 5, 17), "Pfingstmontag"), ("de", D(2027, 10, 3), "Tag der Deutschen Einheit"),
    ("fr", D(2027, 5, 8), "Victoire 1945"), ("fr", D(2027, 5, 17), "Lundi de Pentecôte"),
    ("fr", D(2027, 7, 14), "Fête nationale"), ("fr", D(2027, 11, 11), "Armistice 1918"),
])
def test_germany_and_france_key_dates(cals, code, day, local):
    entry = _on(cals[code], day)
    assert entry and entry.local == local


@pytest.mark.parametrize("code, day, actual", [
    ("gb", D(2027, 5, 31), None), ("gb", D(2027, 8, 30), None),
    ("gb", D(2026, 12, 28), D(2026, 12, 26)),            # Boxing Day 週六 → 週一補假
    ("gb", D(2027, 12, 27), D(2027, 12, 25)), ("gb", D(2027, 12, 28), D(2027, 12, 26)),
    ("au", D(2027, 6, 14), None),                        # King's Birthday（NSW）
    ("au", D(2027, 10, 4), None),                        # Labour Day（NSW）
    ("au", D(2027, 12, 27), D(2027, 12, 25)), ("au", D(2027, 12, 28), D(2027, 12, 26)),
])
def test_uk_and_australia_substitute_days(cals, code, day, actual):
    entry = _on(cals[code], day)
    assert entry is not None, (code, day)
    assert entry.actual == actual


def test_anzac_day_stays_on_25_april_with_an_additional_monday(cals):
    au = cals["au"]
    assert _on(au, D(2027, 4, 25)).name == "Anzac Day"
    assert _on(au, D(2027, 4, 26)).name == "Anzac Day (additional day)"


def test_nsw_bank_holiday_is_not_listed(cals):
    assert _on(cals["au"], D(2027, 8, 2)) is None          # 只有銀行休息，不是公眾假日


@pytest.mark.parametrize("lang", ["ja", "it", "ar"])
def test_every_country_and_city_is_translated(cals, i18n, lang):
    for code in COUNTRIES:
        assert (i18n["countries"].get(code) or {}).get(lang), (code, lang)
        assert (i18n["cities"].get(cals[code].city) or {}).get(lang), (code, lang)


@pytest.mark.parametrize("lang", ["ja", "it", "ar"])
def test_every_holiday_name_is_translated(cals, i18n, lang):
    missing = set()
    for code in COUNTRIES:
        cal = cals[code]
        for e in cal.entries_all:
            if cal.language.split("-")[0] == lang and e.local:
                continue                                    # 當地語言頁面直接用 local
            if not (i18n["holidays"].get(e.name) or {}).get(lang):
                missing.add(e.name)
    assert not missing, sorted(missing)


def test_every_holiday_has_a_chinese_name(cals):
    missing = [(c, e.name) for c in COUNTRIES for e in cals[c].entries_all if not e.name_zh]
    assert not missing


# ---------------------------------------------------------------- 台灣
def test_taiwan_lunar_new_year_is_one_block_including_little_new_years_eve(cals):
    tw = cals["tw"]
    e26, e27 = _on(tw, D(2026, 2, 15)), _on(tw, D(2027, 2, 4))
    assert (e26.end, e27.end) == (D(2026, 2, 20), D(2027, 2, 10))       # 小年夜起算，含補假
    assert e26.name == e27.name == "Lunar New Year"


@pytest.mark.parametrize("day, actual", [
    (D(2026, 2, 27), D(2026, 2, 28)),    # 和平紀念日逢週六 → 前一個上班日補假
    (D(2026, 4, 3), D(2026, 4, 4)),      # 兒童節逢週六
    (D(2026, 4, 6), D(2026, 4, 5)),      # 清明逢週日 → 次一個上班日
    (D(2026, 10, 9), D(2026, 10, 10)),
    (D(2026, 10, 26), D(2026, 10, 25)),
    (D(2027, 3, 1), D(2027, 2, 28)),
    (D(2027, 4, 6), D(2027, 4, 4)),
    (D(2027, 4, 30), D(2027, 5, 1)),
    (D(2027, 10, 11), D(2027, 10, 10)),
    (D(2027, 12, 24), D(2027, 12, 25)),
    (D(2027, 12, 31), D(2028, 1, 1)),    # 117 年元旦逢週六，116 年 12/31 補假
])
def test_taiwan_make_up_holidays(cals, day, actual):
    entry = _on(cals["tw"], day)
    assert entry is not None and entry.actual == actual, day


@pytest.mark.parametrize("day", [D(2026, 5, 1), D(2026, 9, 28), D(2026, 12, 25), D(2027, 9, 28), D(2027, 10, 25)])
def test_taiwan_holidays_added_by_the_2025_act(cals, day):
    assert _on(cals["tw"], day) is not None           # 勞動節、教師節、行憲紀念日、光復節


def test_taiwan_long_breaks_match_the_official_calendar(cals):
    from seoengine.calendar import long_breaks
    spans = {(b.start, b.end) for b in long_breaks(cals["tw"], 2027) if not b.leave_days}
    for span in [(D(2027, 1, 1), D(2027, 1, 3)), (D(2027, 2, 4), D(2027, 2, 10)), (D(2027, 2, 27), D(2027, 3, 1)),
                 (D(2027, 4, 3), D(2027, 4, 6)), (D(2027, 4, 30), D(2027, 5, 2)), (D(2027, 10, 9), D(2027, 10, 11)),
                 (D(2027, 10, 23), D(2027, 10, 25)), (D(2027, 12, 24), D(2027, 12, 26))]:
        assert span in spans, span


def test_taiwan_is_placed_between_uae_and_japan_by_utc(tmp_path):
    import re
    import shutil

    from seoengine.site import build_site
    project = tmp_path / "site"
    shutil.copytree(PROJECT, project, ignore=shutil.ignore_patterns("public", "dashboard", "secrets"))
    out = build_site(project).out_dir
    page = (out / "calendar" / "zh-tw" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'id="tab-([a-z]+)"', page) == ["us", "gb", "it", "de", "fr", "ae", "tw", "jp", "au"]


# ---------------------------------------------------------------- 2028–2029
def test_every_country_has_2028_and_2029(cals):
    for code in COUNTRIES:
        assert {2028, 2029} <= cals[code].years(), code


@pytest.mark.parametrize("code, counts", [
    ("us", (10, 11)), ("gb", (8, 8)), ("it", (13, 13)), ("de", (9, 9)), ("fr", (11, 11)),
    ("ae", (6, 6)), ("tw", (11, 12)), ("jp", (16, 19)), ("au", (11, 11)),
])
def test_2028_2029_counts(cals, code, counts):
    assert (len(cals[code].entries(2028)), len(cals[code].entries(2029))) == counts


def _estimated(cal, year):
    return {e.start for e in cal.entries(year) if e.status == "estimated"}


def test_rule_based_countries_are_official(cals):
    for code in ("us", "it", "de", "fr", "au"):
        assert not _estimated(cals[code], 2028) and not _estimated(cals[code], 2029), code


def test_uk_2028_is_published_but_2029_is_not_yet(cals):
    assert not _estimated(cals["gb"], 2028)
    assert len(_estimated(cals["gb"], 2029)) == 8


def test_taiwan_waits_for_the_official_calendar(cals):
    for year in (2028, 2029):
        assert all(e.status == "estimated" for e in cals["tw"].entries(year)), year


def test_japan_only_equinox_days_are_estimated(cals):
    assert _estimated(cals["jp"], 2028) == {D(2028, 3, 20), D(2028, 9, 22)}
    assert _estimated(cals["jp"], 2029) == {D(2029, 3, 20), D(2029, 9, 23), D(2029, 9, 24)}


def test_uae_islamic_holidays_are_estimated_fixed_ones_are_not(cals):
    ae = cals["ae"]
    assert _on(ae, D(2028, 1, 1)).status == "official"
    assert _on(ae, D(2028, 2, 26)).status == "estimated"
    assert _on(ae, D(2029, 12, 2)).status == "official"


@pytest.mark.parametrize("code, day, actual", [
    ("us", D(2028, 11, 10), D(2028, 11, 11)), ("us", D(2029, 11, 12), D(2029, 11, 11)),
    ("gb", D(2028, 1, 3), D(2028, 1, 1)), ("au", D(2028, 1, 3), D(2028, 1, 1)),
    ("tw", D(2028, 4, 3), D(2028, 4, 4)), ("tw", D(2028, 5, 29), D(2028, 5, 28)),
    ("tw", D(2029, 6, 15), D(2029, 6, 16)), ("tw", D(2029, 9, 21), D(2029, 9, 22)),
])
def test_2028_2029_make_up_days(cals, code, day, actual):
    assert _on(cals[code], day).actual == actual


def test_new_year_2028_is_not_listed_twice(cals):
    for code in ("us", "tw"):                           # 已在 2027/12/31 放假
        assert _on(cals[code], D(2028, 1, 1)) is None, code


def test_italy_sunday_unity_commemoration_is_not_a_day_off(cals):
    assert _on(cals["it"], D(2028, 11, 5)) is None and _on(cals["it"], D(2029, 11, 4)) is None


def test_site_features_years_automatically():
    config = yaml.safe_load((PROJECT / "site.yaml").read_text(encoding="utf-8"))
    assert config["calendar_page"]["year"] == "auto"
