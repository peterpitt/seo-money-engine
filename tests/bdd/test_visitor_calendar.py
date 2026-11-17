import re

import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import write_project
from seoengine.site import build_site
from seoengine.text import strip_html, word_count

scenarios("../../features/calendar_page.feature")


@given(parsers.parse('一個新的網站專案，網址為 "{url}"'))
def given_project(ctx, tmp_path, url):
    ctx["project"] = write_project(tmp_path / "site", base_url=url)


@given("專案有日本與美國的 2027 假日資料")
def given_data(ctx):
    folder = ctx["project"] / "data" / "holidays"
    folder.mkdir(parents=True)
    jp = {"country": "Japan", "country_zh": "日本", "code": "jp", "language": "ja", "short": "Japan",
          "timezone": "Asia/Tokyo", "city": "Tokyo", "city_zh": "東京",
          "holidays": [{"date": "2027-04-29", "name": "Showa Day", "name_zh": "昭和之日", "local": "昭和の日"},
                       {"date": "2027-05-03", "end": "2027-05-05", "name": "Golden Week"}]}
    us = {"country": "United States", "country_zh": "美國", "code": "us", "language": "en", "short": "US",
          "timezone": "America/New_York", "city": "New York", "city_zh": "紐約",
          "holidays": [{"date": "2027-07-05", "actual": "2027-07-04", "name": "Independence Day", "name_zh": "獨立紀念日"}]}
    for code, data in (("jp", jp), ("us", us)):
        (folder / f"{code}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    (folder / "i18n.yaml").write_text(yaml.safe_dump({
        "countries": {"jp": {"ja": "日本", "ar": "اليابان"}, "us": {"ja": "アメリカ", "ar": "الولايات المتحدة"}},
        "holidays": {"Independence Day": {"ja": "独立記念日", "ar": "يوم الاستقلال"},
                     "Golden Week": {"ja": "ゴールデンウィーク"}},
        "cities": {"Tokyo": {"ja": "東京", "ar": "طوكيو"}, "New York": {"ja": "ニューヨーク"}},
    }, allow_unicode=True), encoding="utf-8")


@given(parsers.parse('網站設定行事曆頁面，國家為 "{countries}"，語言為 "{languages}"'))
def given_config(ctx, countries, languages):
    path = ctx["project"] / "site.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["calendar_page"] = {"countries": countries.split(","), "languages": languages.split(","), "year": 2027}
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


@when("我建置網站")
def when_build(ctx):
    ctx["result"] = build_site(ctx["project"])
    ctx["out"] = ctx["result"].out_dir


@then(parsers.parse("行事曆頁面的段落文字應少於 {n:d} 字"))
def then_concise(ctx, n):
    page = (ctx["out"] / "index.html").read_text(encoding="utf-8")
    main = page.split("<main", 1)[1].split("</main>", 1)[0]
    paragraphs = " ".join(strip_html(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", main, re.S))
    assert word_count(paragraphs) < n, paragraphs


def _tabs(page):
    """每張國家卡片（role=tab 的按鈕）的 HTML。"""
    return re.findall(r'<button class="cp-tab[^"]*"[^>]*role="tab".*?</button>', page, re.S)


@then("每個國家只有一張卡片，當地時間就在那張卡片裡")
def then_one_card_per_country(ctx):
    page = (ctx["out"] / "calendar" / "zh-tw" / "index.html").read_text(encoding="utf-8")
    tabs = _tabs(page)
    assert len(tabs) == 2                                   # 背景資料：日本、美國
    jp = next(t for t in tabs if 'id="tab-jp"' in t)
    for part in ('data-tz="Asia/Tokyo"', "東京", "cp-clock-time", "cp-tab-in"):
        assert part in jp, part
    assert 'class="cp-clock"' not in page and "cp-clock-grid" not in page   # 不再有另一排獨立的時間卡片


@then("每張國家卡片都應有指針時鐘，含時針、分針、秒針與上午／下午")
def then_card_analog_clocks(ctx):
    for rel in ("index.html", "calendar/zh-tw/index.html", "calendar/ar/index.html"):
        page = (ctx["out"] / rel).read_text(encoding="utf-8")
        tabs = _tabs(page)
        assert len(tabs) == 2 and sum(t.count('class="an-clock"') for t in tabs) == 2, rel
        for tab in tabs:
            for part in ("an-h", "an-m", "an-s", "an-ampm"):
                assert f'class="{part}"' in tab, (rel, part)


@then("頁首不應有時鐘")
def then_no_header_clock(ctx):
    page = (ctx["out"] / "index.html").read_text(encoding="utf-8")
    header = page.split('<header class="site-header">', 1)[1].split("</header>", 1)[0]
    assert "clock" not in header


@given("行事曆設定依 UTC 時區排序")
def given_sort_utc(ctx):
    path = ctx["project"] / "site.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["calendar_page"]["sort"] = "utc"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


@then(parsers.parse('國家卡片的順序應為 "{codes}"'))
def then_tab_order(ctx, codes):
    page = (ctx["out"] / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'id="tab-([a-z]+)"', page) == codes.split(",")


def _panels(page):
    """每個國家面板（role=tabpanel）的開頭標籤與內容。"""
    return re.findall(r'(<section class="cp-panel[^>]*>)(.*?)</section>', page, re.S)


@then("每個國家的假日面板在靜態頁面都看得到")
def then_panels_visible_without_js(ctx):
    for rel in ("index.html", "calendar/zh-tw/index.html", "calendar/ar/index.html"):
        panels = _panels((ctx["out"] / rel).read_text(encoding="utf-8"))
        assert len(panels) == 2, rel                       # 背景資料：日本、美國
        for tag, body in panels:
            assert " hidden" not in tag, (rel, tag)         # 沒有 JS 時也不能藏起來
            assert 'class="cp-row' in body, (rel, tag)      # 每個面板都有假日列


@given("美國另有 2026 年的假日資料")
def given_us_2026(ctx):
    path = ctx["project"] / "data" / "holidays" / "us.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["holidays"].append({"date": "2026-12-25", "name": "Christmas Day"})
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@then(parsers.parse("每個國家面板的第一個年份區塊都是 {year:d}"))
def then_default_year_block_first(ctx, year):
    panels = _panels((ctx["out"] / "index.html").read_text(encoding="utf-8"))
    assert panels
    for tag, body in panels:
        blocks = re.findall(r'<div class="cp-year" data-year="(\d{4})"', body)
        assert blocks and int(blocks[0]) == year, (tag, blocks)


@then("每個國家聚光燈卡都應有指針時鐘與當地時間")
def then_spotlight_clocks(ctx):
    for rel in ("index.html", "calendar/zh-tw/index.html", "calendar/ar/index.html"):
        page = (ctx["out"] / rel).read_text(encoding="utf-8")
        spots = re.findall(r'(?s)<div class="cp-spotlight">.*?<div class="cp-spotlight-next"', page)
        assert len(spots) == 2, rel                       # 背景資料：日本、美國（都有時區）
        for s in spots:
            assert 'class="cp-spotlight-clock"' in s and "data-tz=" in s, rel
            for part in ("an-h", "an-m", "an-s", "an-ampm", "cp-clock-time"):
                assert f'class="{part}"' in s, (rel, part)
