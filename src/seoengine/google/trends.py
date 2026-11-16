"""Google Trends：
1. 熱門搜尋 RSS（官方公開，免金鑰）：https://trends.google.com/trending/rss?geo=US
2. Explore 匯出的 CSV（multiTimeline.csv）：算旺季月份與最晚發布日
3. 官方 Google Trends API（alpha，需申請）：預留接口，取得存取權與文件後再實作
"""
from __future__ import annotations

import csv
import datetime as dt
import email.utils
import io
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterable
from xml.etree import ElementTree as ET

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
HT = "{https://trends.google.com/trending/rss}"
TRENDS_API_SIGNUP = "https://developers.google.com/search/apis/trends"


class TrendsApiNotAvailable(RuntimeError):
    pass


@dataclass
class TrendingItem:
    title: str
    traffic: int
    traffic_label: str
    published: dt.datetime | None
    geo: str
    news: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"title": self.title, "traffic": self.traffic, "traffic_label": self.traffic_label, "geo": self.geo,
                "published": self.published.isoformat() if self.published else None, "news": self.news}


def parse_traffic(label: str) -> int:
    """'200K+' → 200000、'1M+' → 1000000、'2,000+' → 2000。"""
    m = re.match(r"\s*([\d,.]+)\s*([KkMm]?)", label or "")
    if not m:
        return 0
    value = float(m.group(1).replace(",", ""))
    return int(value * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def _text(node, tag: str) -> str:
    child = node.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def parse_trending_rss(xml_text: str, geo: str) -> list[TrendingItem]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"Google Trends RSS 無法解析（可能被擋或網址錯誤）：{exc}") from exc
    if root.tag != "rss":
        raise ValueError("回應不是 RSS，可能被重新導向或封鎖")
    items = []
    for node in root.iter("item"):
        published = None
        if raw := _text(node, "pubDate"):
            try:
                published = email.utils.parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                published = None
        label = _text(node, f"{HT}approx_traffic")
        items.append(TrendingItem(
            title=_text(node, "title"), traffic=parse_traffic(label), traffic_label=label,
            published=published, geo=geo.upper(),
            news=[{"title": _text(n, f"{HT}news_item_title"), "url": _text(n, f"{HT}news_item_url"),
                   "source": _text(n, f"{HT}news_item_source")} for n in node.findall(f"{HT}news_item")],
        ))
    return items


def _http_get(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "seoengine/0.1 (+trends rss reader)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 固定的官方網址
        return resp.read().decode("utf-8")


def fetch_trending(geo: str, http_get: Callable[[str, float], str] | None = None, timeout: float = 15) -> list[TrendingItem]:
    geo = geo.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}(-[A-Z0-9]{1,3})?", geo):
        raise ValueError(f"geo 必須是國家代碼，例如 US、JP，收到 {geo!r}")
    getter = http_get or _http_get
    return parse_trending_rss(getter(RSS_URL.format(geo=geo), timeout), geo=geo)


def filter_trending(items: Iterable[TrendingItem], include: Iterable[str] = (), exclude: Iterable[str] = ()) -> list[TrendingItem]:
    inc = [p.strip().lower() for p in include if p.strip()]
    exc = [p.strip().lower() for p in exclude if p.strip()]
    out = []
    for item in items:
        title = item.title.lower()
        if inc and not any(p in title for p in inc):
            continue
        if any(p in title for p in exc):
            continue
        out.append(item)
    return out


# ---------------------------------------------------------------- Explore CSV
@dataclass
class InterestSeries:
    keyword: str
    geo: str
    points: list[tuple[dt.date, float]]


_HEADER = re.compile(r"^(?P<kw>.*?)(?::\s*\((?P<geo>[^)]*)\))?$")


def parse_explore_csv(text: str) -> list[InterestSeries]:
    """解析 Google Trends「探索」頁匯出的 CSV（第一欄是日期，其餘欄是各關鍵字，<1 視為 0.5）。"""
    lines = text.lstrip("﻿").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"^(Week|Day|Month|Time|週|日|月|時間)[^,]*,", line.strip())), None)
    if start is None:
        raise ValueError("找不到 Google Trends 資料表頭（第一欄應為 Week / Day / Month）")
    rows = list(csv.reader(io.StringIO("\n".join(lines[start:]))))
    header, data = rows[0], [r for r in rows[1:] if r and r[0].strip()]
    series = []
    for col, label in enumerate(header[1:], start=1):
        m = _HEADER.match(label.strip())
        points = []
        for r in data:
            raw = r[col].strip() if col < len(r) else ""
            if not raw:
                continue
            try:
                day = dt.date.fromisoformat(r[0].strip()[:10]) if len(r[0].strip()) >= 10 else dt.date.fromisoformat(r[0].strip() + "-01")
            except ValueError:
                continue
            points.append((day, 0.5 if raw.startswith("<") else float(raw)))
        series.append(InterestSeries(m.group("kw").strip(), (m.group("geo") or "").strip(), points))
    if not any(s.points for s in series):
        raise ValueError("CSV 裡沒有任何數據")
    return series


@dataclass
class Seasonality:
    keyword: str
    peak_month: int
    monthly_avg: dict[int, float]
    momentum: float
    publish_by: dt.date

    def to_dict(self) -> dict:
        return {"peak_month": self.peak_month, "publish_by": self.publish_by.isoformat(),
                "momentum": round(self.momentum, 3), "monthly_avg": {str(k): round(v, 2) for k, v in self.monthly_avg.items()}}


def seasonality(series: InterestSeries, today: dt.date | None = None, lead_days: int = 42) -> Seasonality:
    """旺季月份＝多年平均最高的月份；最晚發布日＝下一次旺季開始前 6 週（讓 Google 有時間收錄、排名爬升）。"""
    today = today or dt.date.today()
    buckets: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for day, value in series.points:
        buckets[day.month].append(value)
    monthly = {m: (sum(v) / len(v) if v else 0.0) for m, v in buckets.items()}
    peak = max(monthly, key=lambda m: (monthly[m], -m))
    values = [v for _, v in series.points]
    recent, before = values[-4:], values[-16:-4]
    momentum = (sum(recent) / len(recent)) / (sum(before) / len(before)) if before and sum(before) else 1.0
    peak_start = dt.date(today.year, peak, 1)
    if peak_start + dt.timedelta(days=27) < today:
        peak_start = dt.date(today.year + 1, peak, 1)
    return Seasonality(series.keyword, peak, monthly, momentum, peak_start - dt.timedelta(days=lead_days))


# ---------------------------------------------------------------- 官方 API（alpha）
def official_trends_api(keywords: list[str], geo: str, **_kwargs):
    """官方 Google Trends API 目前是封閉 alpha，端點與驗證方式只對核准的測試者公開。

    取得存取權後，把官方文件提供給 Claude，在這裡實作即可；其餘流程（季節性、流量機會）不用改。
    在那之前請用熱門 RSS（seoengine trends trending）與 Explore CSV（seoengine trends import）。
    """
    raise TrendsApiNotAvailable(
        "官方 Google Trends API 仍是封閉 alpha，需要先申請：" + TRENDS_API_SIGNUP +
        "。目前請改用 `seoengine trends trending`（熱門 RSS）與 `seoengine trends import`（Explore 匯出 CSV）。"
    )
