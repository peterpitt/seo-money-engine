"""成效報告：Search Console 優化機會 + 收益彙總（依幣別分開）。"""
from __future__ import annotations

import csv
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .revenue import expected_ctr

_GSC_COLUMNS = {
    "query": ("query", "top queries", "queries", "熱門查詢", "查詢"),
    "clicks": ("clicks", "點擊", "點擊次數"),
    "impressions": ("impressions", "曝光", "曝光次數"),
    "ctr": ("ctr", "點閱率"),
    "position": ("position", "排名", "平均排名"),
}
_GSC_OPTIONAL = {"page": ("page", "top pages", "網頁", "熱門網頁")}


@dataclass(frozen=True)
class QueryStat:
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    page: str = ""

    @property
    def lost_clicks(self) -> float:
        """若點閱率達到該排名應有水準，每月可多拿到的點擊。"""
        return max(0.0, expected_ctr(self.position) - self.ctr) * self.impressions


@dataclass(frozen=True)
class Earning:
    date: dt.date
    page: str
    source: str
    amount: float
    currency: str


def _num(raw) -> float:
    cleaned = re.sub(r"[^\d.\-]", "", str(raw))
    return float(cleaned) if cleaned not in ("", "-", ".") else 0.0


def _ratio(raw) -> float:
    text = str(raw).strip()
    value = _num(text)
    return value / 100 if text.endswith("%") else value


def _pick(row: Mapping, aliases: tuple[str, ...]):
    for alias in aliases:
        if alias in row:
            return row[alias]
    return None


def parse_gsc_rows(rows: Iterable[Mapping]) -> list[QueryStat]:
    stats = []
    for raw in rows:
        row = {str(k).strip().lstrip("﻿").lower(): v for k, v in raw.items() if k is not None}
        values = {}
        for name, aliases in _GSC_COLUMNS.items():
            value = _pick(row, aliases)
            if value is None:
                raise ValueError(f"Search Console 資料缺少欄位: {name}")
            values[name] = value
        stats.append(
            QueryStat(
                query=str(values["query"]).strip(),
                clicks=int(_num(values["clicks"])),
                impressions=int(_num(values["impressions"])),
                ctr=_ratio(values["ctr"]),
                position=_num(values["position"]),
                page=str(_pick(row, _GSC_OPTIONAL["page"]) or ""),
            )
        )
    return stats


def load_gsc_csv(path: str | Path) -> list[QueryStat]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return parse_gsc_rows(csv.DictReader(fh))


def striking_distance(
    stats: Iterable[QueryStat], min_position: float = 8, max_position: float = 20, min_impressions: int = 100
) -> list[QueryStat]:
    """排名 8–20、已有曝光：補內容、加內部連結就最可能衝上第一頁。"""
    picked = [s for s in stats if min_position <= s.position <= max_position and s.impressions >= min_impressions]
    return sorted(picked, key=lambda s: (-s.impressions, s.position))


def ctr_gaps(stats: Iterable[QueryStat], min_impressions: int = 200, ratio: float = 0.5) -> list[QueryStat]:
    """已在第一頁但點閱率不到應有水準一半：改寫標題/描述是最便宜的增量。"""
    picked = [
        s for s in stats
        if s.position <= 10 and s.impressions >= min_impressions and s.ctr < expected_ctr(s.position) * ratio
    ]
    return sorted(picked, key=lambda s: -s.lost_clicks)


def parse_earnings_rows(rows: Iterable[Mapping]) -> list[Earning]:
    out = []
    for raw in rows:
        row = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}
        currency = str(row.get("currency", "")).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(f"currency 必須是 3 碼幣別代號（如 USD、TWD），收到 {row.get('currency')!r}")
        out.append(
            Earning(
                date=dt.date.fromisoformat(str(row["date"]).strip()),
                page=str(row["page"]).strip(),
                source=str(row.get("source", "")).strip(),
                amount=_num(row["amount"]),
                currency=currency,
            )
        )
    return out


def load_earnings_csv(path: str | Path) -> list[Earning]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return parse_earnings_rows(csv.DictReader(fh))


def revenue_by_page(earnings: Iterable[Earning]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for e in earnings:
        bucket = out.setdefault(e.page, {})
        bucket[e.currency] = bucket.get(e.currency, 0.0) + e.amount
    return out


def totals_by_currency(earnings: Iterable[Earning]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for e in earnings:
        totals[e.currency] = totals.get(e.currency, 0.0) + e.amount
    return totals


def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render_report(stats: list[QueryStat], earnings: list[Earning] | None = None, limit: int = 20) -> str:
    parts = [f"# SEO 成效週報（{dt.date.today().isoformat()}）"]

    sd = striking_distance(stats)[:limit]
    parts.append("## 1. 擊殺距離關鍵字（排名 8–20）\n\n動作：補強內容深度、從高權重文章加內部連結、更新日期。")
    parts.append(
        _table(["查詢", "曝光", "點擊", "排名", "網頁"],
               [[s.query, s.impressions, s.clicks, f"{s.position:.1f}", s.page or "—"] for s in sd])
        if sd else "_目前沒有符合條件的關鍵字。_"
    )

    gaps = ctr_gaps(stats)[:limit]
    parts.append("## 2. 點閱率落差（第一頁但 CTR 偏低）\n\n動作：改寫標題（加數字、年份、明確利益）與 meta description。")
    parts.append(
        _table(["查詢", "排名", "實際 CTR", "應有 CTR", "每月可多拿點擊"],
               [[s.query, f"{s.position:.1f}", f"{s.ctr:.1%}", f"{expected_ctr(s.position):.1%}", f"{s.lost_clicks:.0f}"]
                for s in gaps])
        if gaps else "_目前沒有明顯的點閱率落差。_"
    )

    if earnings:
        parts.append("## 3. 收益（依幣別分開，不混算）")
        totals = totals_by_currency(earnings)
        parts.append("總計：" + "、".join(f"{cur} {amt:,.2f}" for cur, amt in sorted(totals.items())))
        by_page = revenue_by_page(earnings)
        rows = sorted(
            ([page, cur, f"{amt:,.2f}"] for page, cur_map in by_page.items() for cur, amt in cur_map.items()),
            key=lambda r: (r[1], -float(r[2].replace(",", ""))),
        )
        parts.append(_table(["頁面", "幣別", "收益"], rows[: limit * 2]))
    return "\n\n".join(parts) + "\n"
