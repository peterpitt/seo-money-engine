import datetime as dt

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md, write_project
from google_fakes import FakeAdsBackend, explore_csv, rss_xml
from seoengine.google.ads import AdsError, KeywordPlanner, ideas_to_rows, write_keywords_csv
from seoengine.google.opportunities import rank_opportunities
from seoengine.google.trends import (
    TrendsApiNotAvailable,
    filter_trending,
    official_trends_api,
    parse_explore_csv,
    parse_trending_rss,
    seasonality,
)
from seoengine.keywords import load_keywords_csv

scenarios("../../features/google_data.feature")


def _rows(datatable):
    header, *rows = datatable
    return [dict(zip(header, r)) for r in rows]


# ---------------------------------------------------------------- Trends
@given("Google Trends 美國熱門 RSS 有以下熱搜:")
def given_rss(ctx, datatable):
    ctx["items"] = parse_trending_rss(rss_xml(_rows(datatable)), geo="US")


@when(parsers.parse('我以主題 "{topics}" 篩選熱搜'))
def when_filter(ctx, topics):
    ctx["result"] = filter_trending(ctx["items"], include=topics.split(","))


@then(parsers.parse('篩選結果依序應為 "{expected}"'))
def then_filtered(ctx, expected):
    assert [i.title for i in ctx["result"]] == [s.strip() for s in expected.split(",")]


@then(parsers.parse('"{title}" 的流量應為 {n:d}'))
def then_traffic(ctx, title, n):
    assert next(i for i in ctx["result"] if i.title == title).traffic == n


@given(parsers.parse('今天是 "{day}"'))
def given_today(ctx, day):
    ctx["today"] = dt.date.fromisoformat(day)


@given(parsers.parse('一份 Google Trends 匯出 CSV，關鍵字 "{kw}" 每年 {month:d} 月最高'))
def given_csv(ctx, kw, month):
    ctx["series"] = parse_explore_csv(explore_csv(kw, peak_month=month))[0]


@when("我分析季節性")
def when_season(ctx):
    ctx["season"] = seasonality(ctx["series"], today=ctx["today"])


@then(parsers.parse("旺季月份應為 {m:d}"))
def then_peak(ctx, m):
    assert ctx["season"].peak_month == m


@then(parsers.parse('建議最晚發布日應為 "{day}"'))
def then_publish_by(ctx, day):
    assert ctx["season"].publish_by.isoformat() == day


# ---------------------------------------------------------------- Ads
@given(parsers.parse('Google Ads 帳戶幣別為 "{cur}"，匯率設定 1 TWD = {rate:g} USD'))
def given_fx(ctx, cur, rate):
    ctx["currency"], ctx["fx"] = cur, {"TWD": rate}


@given(parsers.parse('Google Ads 帳戶幣別為 "{cur}"，沒有設定匯率'))
def given_no_fx(ctx, cur):
    ctx["currency"], ctx["fx"] = cur, {}


@given(parsers.parse('Keyword Planner 對種子 "{seed}" 回傳:'))
def given_ideas(ctx, seed, datatable):
    ctx["seed"] = seed
    ctx["backend"] = FakeAdsBackend(currency=ctx["currency"], ideas=_rows(datatable))


def _generate(ctx, market, tmp_path):
    planner = KeywordPlanner(ctx["backend"], customer_id="1234567890")
    ideas = planner.ideas([ctx["seed"]], country="US", language="en")
    rows = ideas_to_rows(ideas, market=market, currency=planner.account_currency(), fx_to_usd=ctx["fx"])
    path = tmp_path / "keywords.csv"
    write_keywords_csv(rows, path)
    ctx["keywords"] = {k.term: k for k in load_keywords_csv(path)}
    ctx["csv"] = path.read_text(encoding="utf-8")


@when(parsers.parse('我用市場 "{market}" 產生關鍵字檔'))
def when_generate(ctx, market, tmp_path):
    _generate(ctx, market, tmp_path)


@when(parsers.parse('我嘗試用市場 "{market}" 產生關鍵字檔'))
def when_try_generate(ctx, market, tmp_path):
    try:
        _generate(ctx, market, tmp_path)
    except AdsError as exc:
        ctx["error"] = exc


@then(parsers.parse('關鍵字 "{term}" 的搜尋量應為 {n:d}'))
def then_volume(ctx, term, n):
    assert ctx["keywords"][term].volume == n


@then(parsers.parse('關鍵字 "{term}" 的 CPC 應約為 {usd:g} 美元'))
def then_cpc(ctx, term, usd):
    assert ctx["keywords"][term].cpc == pytest.approx(usd, abs=0.001)


@then(parsers.parse('關鍵字 "{term}" 的難度應為 {n:d}'))
def then_kd(ctx, term, n):
    assert ctx["keywords"][term].difficulty == n


@then(parsers.parse('關鍵字檔應標示資料來源為 "{source}"'))
def then_source(ctx, source):
    assert ctx["csv"].splitlines()[0].endswith(",source") or ",source," in ctx["csv"].splitlines()[0]
    assert all(line.split(",")[5] == source for line in ctx["csv"].splitlines()[1:])


@then(parsers.parse('應出現錯誤，訊息包含 "{text}"'))
def then_error(ctx, text):
    assert "error" in ctx and text in str(ctx["error"])


# ---------------------------------------------------------------- 流量機會
@given(parsers.parse('一個新的網站專案，網址為 "{url}"'))
def given_project(ctx, tmp_path, url):
    ctx["project"] = write_project(tmp_path / "site", base_url=url)


@given(parsers.parse('專案已有一篇文章，關鍵字為 "{kw}"'))
def given_existing(ctx, kw):
    (ctx["project"] / "content" / "existing.md").write_text(article_md("existing", kw, lang="en"), encoding="utf-8")


@given("專案的關鍵字檔來自 Google Ads:")
def given_project_keywords(ctx, datatable):
    rows = [",".join(r + (["source"] if i == 0 else ["google-ads"])) for i, r in enumerate(datatable)]
    (ctx["project"] / "keywords.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


@given(parsers.parse('熱搜中有 "{title}"'))
def given_trending(ctx, title):
    ctx["trending"] = parse_trending_rss(rss_xml([{"title": title, "traffic": "20K+"}]), geo="AE")


@when(parsers.parse("我計算流量機會並為前 {n:d} 名產生文章骨架"))
def when_rank(ctx, n):
    ctx["opps"] = rank_opportunities(ctx["project"], trending=ctx["trending"], brief_top=n)


@then(parsers.parse('第一名應為 "{term}"，並標示為熱搜中'))
def then_first(ctx, term):
    first = ctx["opps"][0]
    assert first.term == term and first.trending


@then(parsers.parse('"{term}" 應標示已有文章'))
def then_covered(ctx, term):
    assert next(o for o in ctx["opps"] if o.term == term).covered_by == "existing"


@then(parsers.parse('應產生草稿 "{name}"'))
def then_draft(ctx, name):
    text = (ctx["project"] / "content" / name).read_text(encoding="utf-8")
    assert "draft: true" in text


@when("我呼叫官方 Google Trends API")
def when_official(ctx):
    try:
        official_trends_api(["public holidays"], geo="US")
    except TrendsApiNotAvailable as exc:
        ctx["error"] = exc
