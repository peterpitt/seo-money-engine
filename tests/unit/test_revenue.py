import pytest

from seoengine.keywords import Keyword
from seoengine.revenue import (
    DEFAULT_ECONOMICS,
    MarketEconomics,
    expected_ctr,
    forecast,
    portfolio_totals,
)


def test_expected_ctr_monotonic_on_page_one():
    values = [expected_ctr(p) for p in range(1, 11)]
    assert values == sorted(values, reverse=True)


def test_expected_ctr_beyond_page_one():
    assert expected_ctr(15) < expected_ctr(10)
    assert expected_ctr(35) < expected_ctr(15)


def test_expected_ctr_rejects_invalid():
    with pytest.raises(ValueError):
        expected_ctr(0)


def test_forecast_math():
    econ = MarketEconomics(currency="USD", rpm=10, affiliate_ctr=0.1, conversion_rate=0.05, avg_commission=20)
    kw = Keyword("best grinder", 10_000, 1.0, 10, market="us")  # commercial factor 1.0
    f = forecast(kw, position=1, economics=econ)
    clicks = 10_000 * expected_ctr(1)
    assert f.clicks == pytest.approx(clicks)
    assert f.ad_revenue == pytest.approx(clicks / 1000 * 10)
    assert f.affiliate_revenue == pytest.approx(clicks * 0.1 * 0.05 * 20)
    assert f.total == pytest.approx(f.ad_revenue + f.affiliate_revenue)
    assert f.currency == "USD"


def test_informational_earns_less_affiliate_than_commercial():
    info = forecast(Keyword("how to clean grinder", 1000, 1, 10, market="us"), position=3)
    comm = forecast(Keyword("best grinder", 1000, 1, 10, market="us"), position=3)
    assert info.affiliate_revenue < comm.affiliate_revenue


def test_default_economics_by_market():
    assert DEFAULT_ECONOMICS["tw"].currency == "TWD"
    assert DEFAULT_ECONOMICS["us"].currency == "USD"


def test_portfolio_totals_never_mix_currencies():
    fs = [
        forecast(Keyword("best grinder", 1000, 1, 10, market="us"), position=3),
        forecast(Keyword("磨豆機推薦", 1000, 1, 10, market="tw"), position=3),
    ]
    totals = portfolio_totals(fs)
    assert totals["USD"] == pytest.approx(fs[0].total)
    assert totals["TWD"] == pytest.approx(fs[1].total)
