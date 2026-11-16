import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from seoengine.report import (
    ctr_gaps,
    parse_earnings_rows,
    parse_gsc_rows,
    revenue_by_page,
    striking_distance,
    totals_by_currency,
)
from seoengine.revenue import expected_ctr, forecast, portfolio_totals

scenarios("../../features/performance_report.feature")


def _rows(datatable):
    header, *rows = datatable
    return [dict(zip(header, row)) for row in rows]


@given("Search Console 匯出資料:")
def given_gsc(ctx, datatable):
    ctx["stats"] = parse_gsc_rows(_rows(datatable))


@when("我分析擊殺距離關鍵字")
def when_striking(ctx):
    ctx["result"] = striking_distance(ctx["stats"])


@when("我分析點閱率落差")
def when_ctr_gap(ctx):
    ctx["result"] = ctr_gaps(ctx["stats"])


@given("收益明細:")
def given_earnings(ctx, datatable):
    ctx["earnings"] = parse_earnings_rows(_rows(datatable))


@when("我彙總每頁收益")
def when_revenue(ctx):
    ctx["by_page"] = revenue_by_page(ctx["earnings"])
    ctx["totals"] = totals_by_currency(ctx["earnings"])


@then(parsers.parse('"{page}" 的 {currency} 收益應為 {amount:g}'))
def then_page_revenue(ctx, page, currency, amount):
    assert ctx["by_page"][page][currency] == pytest.approx(amount)


@then(parsers.parse("{currency} 總收益應為 {amount:g}"))
def then_total(ctx, currency, amount):
    assert ctx["totals"][currency] == pytest.approx(amount)


@when(parsers.parse("我以目標排名第 {pos:d} 名預估月收益"))
def when_forecast(ctx, pos):
    ctx["position"] = pos
    ctx["forecasts"] = [forecast(k, position=pos) for k in ctx["keywords"]]
    ctx["totals"] = portfolio_totals(ctx["forecasts"])


@then(parsers.parse('預估結果應同時有 "{a}" 與 "{b}" 兩種幣別'))
def then_currencies(ctx, a, b):
    assert set(ctx["totals"]) == {a, b}


@then(parsers.parse("每個關鍵字的預估點擊應等於搜尋量乘以第 {pos:d} 名點閱率"))
def then_clicks(ctx, pos):
    for f in ctx["forecasts"]:
        assert f.clicks == pytest.approx(f.keyword.volume * expected_ctr(pos))
