"""收益預估：排名 → 點擊 → AdSense + 聯盟分潤，依幣別分開計算。

所有預設數字都是「保守的起始假設」，請用你自己的 Search Console 與收益報表回填校正。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .keywords import Intent, Keyword

# 第 1–10 名的自然點閱率（綜合多份公開 CTR 研究的保守值）
CTR_BY_POSITION = {
    1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.06,
    6: 0.045, 7: 0.035, 8: 0.028, 9: 0.024, 10: 0.02,
}

AFFILIATE_INTENT_FACTOR = {
    Intent.TRANSACTIONAL: 1.2,
    Intent.COMMERCIAL: 1.0,
    Intent.INFORMATIONAL: 0.25,
    Intent.NAVIGATIONAL: 0.0,
}


def expected_ctr(position: float) -> float:
    if position < 1:
        raise ValueError("position must be >= 1")
    rank = int(round(position))
    if rank in CTR_BY_POSITION:
        return CTR_BY_POSITION[rank]
    if rank <= 20:
        return 0.01
    return 0.002


@dataclass(frozen=True)
class MarketEconomics:
    currency: str
    rpm: float               # 每千次頁面瀏覽的 AdSense 收益（該幣別）
    affiliate_ctr: float     # 讀者點擊聯盟連結的比例
    conversion_rate: float   # 點擊後成交比例
    avg_commission: float    # 平均每筆佣金（該幣別）


DEFAULT_ECONOMICS = {
    "tw": MarketEconomics(currency="TWD", rpm=60, affiliate_ctr=0.08, conversion_rate=0.03, avg_commission=150),
    "us": MarketEconomics(currency="USD", rpm=12, affiliate_ctr=0.10, conversion_rate=0.04, avg_commission=8),
}


@dataclass(frozen=True)
class RevenueForecast:
    keyword: Keyword
    position: float
    clicks: float
    ad_revenue: float
    affiliate_revenue: float
    currency: str

    @property
    def total(self) -> float:
        return self.ad_revenue + self.affiliate_revenue


def forecast(kw: Keyword, position: float = 3, economics: MarketEconomics | None = None) -> RevenueForecast:
    econ = economics or DEFAULT_ECONOMICS[kw.market]
    clicks = kw.volume * expected_ctr(position)
    ad = clicks / 1000 * econ.rpm
    aff = (
        clicks * econ.affiliate_ctr * AFFILIATE_INTENT_FACTOR[kw.intent]
        * econ.conversion_rate * econ.avg_commission
    )
    return RevenueForecast(kw, position, clicks, ad, aff, econ.currency)


def portfolio_totals(forecasts: Iterable[RevenueForecast]) -> dict[str, float]:
    """依幣別加總——美金與台幣永不混算。"""
    totals: dict[str, float] = {}
    for f in forecasts:
        totals[f.currency] = totals.get(f.currency, 0.0) + f.total
    return totals
