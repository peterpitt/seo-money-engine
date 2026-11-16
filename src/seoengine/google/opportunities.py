"""流量機會：把 Keyword Planner（量與出價）、Trends 熱搜（正在升溫）、Trends 季節性（何時要上線）合在一起排名。

分數 = 錢景分數（量 × CPC × 意圖 × 可排名機率²）× 熱搜加成 1.5 × 旺季將至加成 1.2
已經有文章的主題排在最後（不是新機會），並標示是哪一篇。
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from ..briefs import create_brief
from ..content import load_articles
from ..keywords import Keyword, load_keywords_csv, opportunity_score, site_fx
from ..revenue import forecast
from ..text import slugify, tokens
from .trends import TrendingItem

TREND_BOOST = 1.5
URGENT_BOOST = 1.2
URGENT_WINDOW_DAYS = 60


@dataclass
class Opportunity:
    term: str
    market: str
    intent: str
    volume: int
    cpc: float
    difficulty: int
    score: float
    forecast_total: float
    currency: str
    trending: str | None = None
    peak_month: int | None = None
    publish_by: str | None = None
    urgent: bool = False
    covered_by: str | None = None
    brief_path: str | None = None


def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    a_l, b_l = a.lower(), b.lower()
    if a_l in b_l or b_l in a_l:
        return True
    ta, tb = tokens(a_l), tokens(b_l)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= threshold


def _load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def rank_opportunities(project_dir: str | Path, trending: Iterable[TrendingItem] | None = None,
                       today: dt.date | None = None, brief_top: int = 0) -> list[Opportunity]:
    project = Path(project_dir)
    today = today or dt.date.today()
    kw_path = project / "keywords.csv"
    if not kw_path.exists():
        raise FileNotFoundError(
            f"找不到 {kw_path}。請先執行 `seoengine ads ideas --project {project}` 用 Google Ads 取得真實關鍵字數據。")
    keywords: list[Keyword] = load_keywords_csv(kw_path, fx_to_usd=site_fx(project))
    data_dir = project / "data"
    if trending is None:
        trending = [TrendingItem(t["title"], t.get("traffic", 0), t.get("traffic_label", ""), None, t.get("geo", ""))
                    for t in _load_json(data_dir / "trending.json", [])]
    trending = list(trending)
    seasons: dict = _load_json(data_dir / "seasonality.json", {})
    articles = load_articles(project / "content")

    opps = []
    for k in keywords:
        hot = next((t for t in trending if _similar(k.term, t.title)), None)
        season_key = next((name for name in seasons if _similar(k.term, name, 0.5)), None)
        season = seasons.get(season_key) if season_key else None
        urgent = False
        if season and season.get("publish_by"):
            days_left = (dt.date.fromisoformat(season["publish_by"]) - today).days
            urgent = days_left <= URGENT_WINDOW_DAYS
        score = opportunity_score(k) * (TREND_BOOST if hot else 1) * (URGENT_BOOST if urgent else 1)
        covered = next((a.slug for a in articles if _similar(k.term, a.keyword, 0.75)), None)
        f = forecast(k, position=3)
        opps.append(Opportunity(
            term=k.term, market=k.market, intent=k.intent.value, volume=k.volume, cpc=k.cpc, difficulty=k.difficulty,
            score=round(score, 2), forecast_total=round(f.total, 2), currency=f.currency,
            trending=hot.title if hot else None,
            peak_month=season.get("peak_month") if season else None,
            publish_by=season.get("publish_by") if season else None,
            urgent=urgent, covered_by=covered,
        ))
    opps.sort(key=lambda o: (o.covered_by is not None, -o.score))

    created = 0
    for o in opps:
        if created >= brief_top:
            break
        if o.covered_by:
            continue
        try:
            path, _ = create_brief(project, o.term, o.market, slugify(o.term))
        except FileExistsError:
            continue
        o.brief_path = str(path)
        created += 1

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "opportunities.json").write_text(
        json.dumps([asdict(o) for o in opps], ensure_ascii=False, indent=2), encoding="utf-8")
    return opps
