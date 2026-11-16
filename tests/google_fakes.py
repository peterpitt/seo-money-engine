"""測試用的 Google 假資料：RSS、Explore CSV、Google Ads 後端（不連網、不需要金鑰）。"""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from xml.sax.saxutils import escape


def rss_xml(items: list[dict]) -> str:
    """產生與 trends.google.com/trending/rss 相同結構的 XML。"""
    body = "".join(
        "<item>"
        f"<title>{escape(i['title'])}</title>"
        f"<ht:approx_traffic>{escape(i['traffic'])}</ht:approx_traffic>"
        "<description/><link>https://trends.google.com/trending/rss?geo=US</link>"
        "<pubDate>Thu, 22 Oct 2026 23:30:00 -0700</pubDate>"
        "<ht:picture>https://example.com/p.jpg</ht:picture><ht:picture_source>ESPN</ht:picture_source>"
        "<ht:news_item><ht:news_item_title>Story about "
        f"{escape(i['title'])}</ht:news_item_title><ht:news_item_snippet/>"
        "<ht:news_item_url>https://news.example.com/a</ht:news_item_url>"
        "<ht:news_item_source>Example News</ht:news_item_source></ht:news_item>"
        "</item>"
        for i in items
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:ht="https://trends.google.com/trending/rss" version="2.0">'
            f"<channel><title>Daily Search Trends</title>{body}</channel></rss>")


def explore_csv(keyword: str, peak_month: int, years: int = 3, geo: str = "United States") -> str:
    """Google Trends Explore 匯出的 multiTimeline.csv：每週一筆，指定月份最高。"""
    start = dt.date(2023, 10, 29)
    lines = ["Category: All categories", "", f"Week,{keyword}: ({geo})"]
    for w in range(52 * years):
        day = start + dt.timedelta(weeks=w)
        value = 100 if day.month == peak_month else 60 if day.month in ((peak_month - 2) % 12 + 1, peak_month % 12 + 1) else 20
        lines.append(f"{day.isoformat()},{value if w % 7 else '<1' if value == 20 else value}")
    return "\n".join(lines) + "\n"


class FakeAdsBackend:
    """模擬 Google Ads API：GAQL 查詢與 GenerateKeywordIdeas。"""

    def __init__(self, currency: str = "USD", ideas: list[dict] | None = None):
        self.currency = currency
        self._ideas = ideas or []
        self.queries: list[str] = []
        self.requests: list[dict] = []

    def search(self, customer_id: str, query: str):
        self.queries.append(query)
        if "FROM customer" in query:
            return [SimpleNamespace(customer=SimpleNamespace(currency_code=self.currency))]
        if "FROM geo_target_constant" in query:
            return [SimpleNamespace(geo_target_constant=SimpleNamespace(resource_name="geoTargetConstants/2840"))]
        if "FROM language_constant" in query:
            return [SimpleNamespace(language_constant=SimpleNamespace(resource_name="languageConstants/1000"))]
        return []

    def generate_keyword_ideas(self, customer_id: str, seeds: list[str], url: str | None,
                               geo_resource_names: list[str], language_resource_name: str, limit: int):
        self.requests.append({"customer_id": customer_id, "seeds": seeds, "url": url,
                              "geos": geo_resource_names, "language": language_resource_name})
        for row in self._ideas[:limit]:
            yield SimpleNamespace(text=row["text"], keyword_idea_metrics=SimpleNamespace(
                avg_monthly_searches=int(row["avg_monthly_searches"]),
                competition_index=int(row["competition_index"]),
                low_top_of_page_bid_micros=int(row["low_bid_micros"]),
                high_top_of_page_bid_micros=int(row["high_bid_micros"]),
                average_cpc_micros=0,
            ))
