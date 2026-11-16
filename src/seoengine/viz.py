"""站長收益儀表板（只給自己看、不部署）：流水線狀態、待公告假日與雙軌收益預估，打包成可離線開啟的 HTML。

給訪客的假日時間軸在公開網站上（[[timeline]] 短碼），不在這裡。

所有數字都由引擎（calendar / quality / revenue）計算後內嵌，頁面上的 JavaScript 只負責呈現與動畫，
所以儀表板顯示的結果一定和 CLI 一致。
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .calendar import load_calendars
from .content import load_articles
from .keywords import load_keywords_csv, opportunity_score, site_fx
from .monetize import load_offers
from .quality import check_article
from .revenue import forecast
from .site import SiteConfig

TEMPLATE = Path(__file__).parent / "templates" / "dashboard.html"
_DATA_TAG = re.compile(r'<script type="application/json" id="viz-data">(.*?)</script>', re.S)
_OFFER_REF = re.compile(r"\[\[(?:offer|cta|compare):([^\]|]+)")



PENDING_HORIZON_DAYS = 400   # 只列未來約 13 個月內的預估假日，更遠的（例如兩年後的台灣假日）只計數


def _pending(project: Path, today: dt.date) -> tuple[list[dict], int]:
    """還在等官方公告的預估假日：公告後要更新 data/holidays/<code>.yaml。回傳（近期清單, 更遠的數量）。"""
    rows, later = [], 0
    horizon = today + dt.timedelta(days=PENDING_HORIZON_DAYS)
    for code, cal in load_calendars(project).items():
        for e in cal.entries_all:
            if e.status != "estimated":
                continue
            if e.start > horizon:
                later += 1
                continue
            rows.append({"code": code, "country": cal.country_zh or cal.country, "name": e.name_zh or e.name,
                         "start": e.start.isoformat(), "end": e.end.isoformat()})
    return sorted(rows, key=lambda r: (r["start"], r["code"])), later


def _pipeline(project: Path, cfg: SiteConfig, keywords: list) -> dict:
    offers = load_offers(project / "offers.yaml")
    articles = load_articles(project / "content")
    live = [a for a in articles if not a.draft]
    reports = {a.slug: check_article(a, offers, cfg.quality) for a in live}
    published = [a for a in live if reports[a.slug].passed]

    used: dict[str, int] = {}
    for a in published:
        ids = {i.strip() for ref in _OFFER_REF.findall(a.body_md) for i in ref.split(",")}
        for oid in ids & set(offers):
            used[oid] = used.get(oid, 0) + 1

    configured = [name for name, ok in (("GA4", bool(cfg.ga4)), ("AdSense", cfg.adsense.enabled)) if ok]
    passed, failed = len(published), len(live) - len(published)
    stages = [
        {"id": "keywords", "label": "關鍵字", "value": len(keywords),
         "caption": "已評估錢景" if keywords else "尚未提供關鍵字檔",
         "detail": [{"label": k.term, "meta": f"{k.market.upper()} · {k.intent.value} · 錢景 {opportunity_score(k):,.0f}"}
                    for k in sorted(keywords, key=opportunity_score, reverse=True)[:8]]},
        {"id": "articles", "label": "文章", "value": len(articles),
         "caption": f"草稿 {len(articles) - len(live)} 篇",
         "detail": [{"label": a.title, "meta": "草稿" if a.draft else a.lang} for a in articles]},
        {"id": "gate", "label": "品質閘門", "value": passed, "passed": passed, "failed": failed,
         "caption": f"通過 {passed} · 擋下 {failed}",
         "detail": [{"slug": a.slug, "label": a.title, "passed": reports[a.slug].passed,
                     "rules": sorted({i.rule for i in reports[a.slug].errors}),
                     "meta": f"分數 {reports[a.slug].score}"} for a in live]},
        {"id": "monetize", "label": "變現", "value": len(used),
         "caption": f"聯盟商品 {len(offers)} 個",
         "detail": [{"label": offers[o].name, "meta": f"{offers[o].network or '聯盟'} · 用在 {n} 篇"}
                    for o, n in sorted(used.items())]},
        {"id": "build", "label": "建置", "value": len(published) + 2 + len(used),
         "caption": f"sitemap {len(published) + 1} 個網址",
         "detail": [{"label": f"/{a.slug}/", "meta": "文章"} for a in published]
                   + [{"label": "/", "meta": "首頁"}, {"label": "/404.html", "meta": "錯誤頁"}]
                   + [{"label": f"/go/{o}/", "meta": "聯盟跳轉頁（noindex）"} for o in sorted(used)]},
        {"id": "measure", "label": "成效", "value": len(configured),
         "caption": f"已串接 {len(configured)} / 2",
         "detail": [{"label": "Google Search Console", "meta": "匯出 CSV → seoengine report"},
                    {"label": "GA4", "meta": f"已設定 {cfg.ga4}" if cfg.ga4 else "未設定（site.yaml analytics.ga4）"},
                    {"label": "AdSense", "meta": "已設定" if cfg.adsense.enabled else "未設定（審核通過後填 adsense.client）"}]},
    ]
    return {"stages": stages}


def _provider(path) -> str:
    """keywords.csv 的資料來源：全部來自 Google Ads 時標成 google-ads，否則 manual。"""
    from .keywords import _read_rows

    if not path:
        return "manual"
    rows = _read_rows(path)
    if rows and "source" not in rows[0]:
        # 直接用 Google Ads 關鍵字規劃工具的匯出檔
        header = " ".join(rows[0]).lower()
        planner = any(n in header for n in ("monthly searches", "每月搜索量", "每月搜尋量"))
        return "google-ads" if planner else "manual"
    sources = {(row.get("source") or "").strip() for row in rows}
    return "google-ads" if sources == {"google-ads"} else "manual"


def _json_file(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _revenue(keywords: list, source: str | None, provider: str = "manual") -> dict | None:
    if not keywords:
        return None
    rows = []
    for k in keywords:
        curve = []
        for pos in range(1, 21):
            f = forecast(k, position=pos)
            curve.append({"pos": pos, "clicks": round(f.clicks, 4),
                          "ad": round(f.ad_revenue, 6), "aff": round(f.affiliate_revenue, 6)})
        rows.append({"term": k.term, "market": k.market, "currency": forecast(k).currency,
                     "intent": k.intent.value, "volume": k.volume, "cpc": k.cpc,
                     "difficulty": k.difficulty, "curve": curve})
    return {"source": source, "provider": provider, "example": "example" in (source or "").lower(), "keywords": rows}


def build_dashboard_data(project_dir: str | Path, keywords_path: str | Path | None = None,
                         today: dt.date | None = None) -> dict:
    project = Path(project_dir)
    today = today or dt.date.today()
    pending, pending_later = _pending(project, today)
    cfg = SiteConfig.load(project / "site.yaml")
    if keywords_path is None:
        for name in ("keywords.csv", "keywords.example.csv"):
            if (project / name).exists():
                keywords_path = project / name
                break
    keywords = load_keywords_csv(keywords_path, fx_to_usd=site_fx(project)) if keywords_path else []
    return {
        "site": {"name": cfg.name, "base_url": cfg.base_url},
        "generated": today.isoformat(),
        "pending": pending,
        "pending_later": pending_later,
        "pipeline": _pipeline(project, cfg, keywords),
        "revenue": _revenue(keywords, Path(keywords_path).name if keywords_path else None, _provider(keywords_path)),
        "opportunities": _json_file(project / "data" / "opportunities.json", [])[:15],
        "trending": _json_file(project / "data" / "trending.json", [])[:12],
    }


def _embed(data: dict) -> str:
    # 把 < 轉成 <，避免任何字串提前關閉 <script>
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def render_dashboard(data: dict, standalone: bool = True) -> str:
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*__VIZ_DATA__*/", _embed(data), 1)
    if not standalone:
        return body
    return (
        '<!doctype html>\n<html lang="zh-TW">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


def extract_data(page: str) -> dict:
    m = _DATA_TAG.search(page)
    if not m:
        raise ValueError("no embedded dashboard data")
    return json.loads(m.group(1))


def write_dashboard(project_dir: str | Path, keywords_path: str | Path | None = None,
                    out: str | Path | None = None, standalone: bool = True) -> Path:
    project = Path(project_dir)
    target = Path(out) if out else project / "dashboard" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(build_dashboard_data(project, keywords_path), standalone), encoding="utf-8")
    return target
