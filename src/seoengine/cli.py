"""seoengine 指令列工具。

  seoengine init <dir>                 建立新站（含範例內容、設定、聯盟商品表）
  seoengine keywords <csv>             關鍵字錢景排序 / 分群
  seoengine forecast <csv>             依目標排名預估雙幣別月收益
  seoengine brief "<keyword>"          依搜尋意圖產生文章骨架（draft）
  seoengine check [dir]                執行品質閘門
  seoengine build [dir]                建置靜態網站
  seoengine report --gsc <csv>         產生優化週報
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

import yaml

from .content import ContentError, load_articles
from .keywords import Intent, Keyword, cluster_keywords, load_keywords_csv, opportunity_score, prioritize
from .monetize import load_offers
from .quality import check_article
from .report import load_earnings_csv, load_gsc_csv, render_report
from .revenue import forecast, portfolio_totals
from .site import BuildError, SiteConfig, build_site
from .text import slugify

SCAFFOLD = Path(__file__).parent / "scaffold"


def _err(msg: str) -> int:
    print(f"錯誤：{msg}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------- init
def cmd_init(args) -> int:
    target = Path(args.directory)
    if target.exists() and any(target.iterdir()):
        return _err(f"{target} 不是空資料夾")
    shutil.copytree(SCAFFOLD, target, dirs_exist_ok=True)
    print(f"已建立網站專案：{target}\n下一步：編輯 site.yaml 的 base_url，然後執行 seoengine build {target}")
    return 0


# ---------------------------------------------------------------- keywords / forecast
def _fx_args(pairs: list[str] | None) -> dict[str, float]:
    out = {}
    for pair in pairs or []:
        cur, _, rate = pair.partition("=")
        out[cur.strip().upper()] = float(rate)
    return out


def _load_kw(args):
    return load_keywords_csv(args.csv, fx_to_usd=_fx_args(args.fx), market=args.market)


def cmd_keywords(args) -> int:
    try:
        kws = _load_kw(args)
    except (ValueError, OSError) as exc:
        return _err(str(exc))
    ranked = prioritize(kws, max_difficulty=args.max_kd, min_volume=args.min_volume, top=args.top)
    print(f"{'#':>3}  {'市場':<4} {'意圖':<14} {'量':>7} {'CPC':>6} {'KD':>4} {'錢景分數':>10} {'第3名月收益':>16}  關鍵字")
    for i, k in enumerate(ranked, 1):
        f = forecast(k, position=3)
        print(f"{i:>3}  {k.market:<4} {k.intent.value:<14} {k.volume:>7} {k.cpc:>6.2f} {k.difficulty:>4} "
              f"{opportunity_score(k):>10.1f} {f.currency:>4} {f.total:>11,.0f}  {k.term}")
    if args.clusters:
        print("\n主題群（第一個 = 支柱頁）：")
        for n, cluster in enumerate(cluster_keywords(ranked), 1):
            print(f"  [{n}] " + " / ".join(k.term for k in cluster))
    return 0


def cmd_forecast(args) -> int:
    try:
        fs = [forecast(k, position=args.position) for k in _load_kw(args)]
    except (ValueError, OSError) as exc:
        return _err(str(exc))
    for f in sorted(fs, key=lambda f: -f.total):
        print(f"{f.currency} {f.total:>10,.0f}  (廣告 {f.ad_revenue:,.0f} + 聯盟 {f.affiliate_revenue:,.0f}, "
              f"點擊 {f.clicks:,.0f})  {f.keyword.term}")
    print(f"\n目標排名第 {args.position} 名的預估月收益：")
    for cur, total in sorted(portfolio_totals(fs).items()):
        print(f"  {cur} {total:,.0f}")
    print("（假設值可在 revenue.py 的 DEFAULT_ECONOMICS 調整，並用實際報表校正）")
    return 0


# ---------------------------------------------------------------- brief
def cmd_brief(args) -> int:
    from .briefs import create_brief

    try:
        path, intent = create_brief(Path(args.project), args.keyword, args.market, args.slug)
    except FileExistsError as exc:
        return _err(f"{exc} 已存在，不覆蓋")
    print(f"已建立文章骨架（{intent.value}）：{path}\n寫完後把 draft 改成 false，並補上 description。")
    return 0


# ---------------------------------------------------------------- check / build
def cmd_check(args) -> int:
    project = Path(args.project)
    try:
        cfg = SiteConfig.load(project / "site.yaml")
        offers = load_offers(project / "offers.yaml")
        articles = load_articles(project / "content")
    except (BuildError, ContentError, ValueError) as exc:
        return _err(str(exc))
    failed = 0
    for a in articles:
        if a.draft and not args.include_drafts:
            continue
        r = check_article(a, offers, cfg.quality)
        mark = "PASS" if r.passed else "FAIL"
        failed += not r.passed
        print(f"[{mark}] {a.slug:<32} 分數 {r.score:>3}  {a.title}")
        for issue in r.issues:
            print(f"        - {issue.severity:<7} {issue.rule:<18} {issue.message}")
    print(f"\n共 {len(articles)} 篇，{failed} 篇未通過品質閘門")
    return 1 if failed else 0


def cmd_build(args) -> int:
    try:
        result = build_site(args.project, out_dir=args.out, force=args.force)
    except BuildError as exc:
        return _err(str(exc))
    print(f"已發布 {len(result.published)} 篇 → {result.out_dir}")
    for slug, reason in result.skipped.items():
        print(f"  略過 {slug}: {reason}")
    return 0


def cmd_report(args) -> int:
    stats = load_gsc_csv(args.gsc)
    earnings = load_earnings_csv(args.earnings) if args.earnings else None
    md = render_report(stats, earnings)
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"報告已寫入 {args.output}")
    else:
        print(md)
    return 0


def cmd_viz(args) -> int:
    from .viz import write_dashboard

    try:
        path = write_dashboard(args.project, keywords_path=args.keywords, out=args.output)
    except (BuildError, ContentError, ValueError) as exc:
        return _err(str(exc))
    print(f"儀表板已產生：{path}\n用瀏覽器直接開啟這個檔案即可（不需要伺服器）。")
    return 0


# ---------------------------------------------------------------- Google 資料
def _site_google(project: Path) -> dict:
    data = yaml.safe_load((project / "site.yaml").read_text(encoding="utf-8")) if (project / "site.yaml").exists() else {}
    return data or {}


def cmd_trends_trending(args) -> int:
    import json

    from .google.trends import fetch_trending, filter_trending

    project = Path(args.project)
    conf = (_site_google(project).get("trends") or {})
    geos = [g for g in (args.geo or ",".join(conf.get("geos") or ["US"])).split(",") if g.strip()]
    include = args.include.split(",") if args.include else list(conf.get("include") or [])
    exclude = args.exclude.split(",") if args.exclude else list(conf.get("exclude") or [])
    found = []
    for geo in geos:
        try:
            items = fetch_trending(geo)
        except (OSError, ValueError) as exc:
            print(f"  {geo}: 讀取失敗（{exc}）", file=sys.stderr)
            continue
        kept = filter_trending(items, include, exclude)
        print(f"{geo.upper()}：熱搜 {len(items)} 筆，符合主題 {len(kept)} 筆")
        for item in kept:
            print(f"  {item.traffic_label:>6}  {item.title}")
        found += kept
    out = project / "data" / "trending.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([i.to_dict() for i in found], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已存到 {out}")
    return 0


def cmd_trends_import(args) -> int:
    import json

    from .google.trends import parse_explore_csv, seasonality

    project = Path(args.project)
    text = Path(args.csv).read_text(encoding="utf-8-sig")
    out = project / "data" / "seasonality.json"
    saved = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for series in parse_explore_csv(text):
        s = seasonality(series)
        saved[series.keyword] = s.to_dict()
        print(f"{series.keyword}（{series.geo or '全球'}）：旺季 {s.peak_month} 月，最晚 {s.publish_by} 上線，"
              f"近期熱度是先前的 {s.momentum:.0%}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已存到 {out}")
    return 0


def cmd_trends_api(args) -> int:
    from .google.trends import TrendsApiNotAvailable, official_trends_api

    try:
        official_trends_api(args.keywords.split(","), geo=args.geo)
    except TrendsApiNotAvailable as exc:
        return _err(str(exc))
    return 0  # pragma: no cover


def cmd_ads_auth(args) -> int:
    from .google.auth import create_ads_yaml

    try:
        path = create_ads_yaml(args.client_secrets, args.developer_token, args.customer_id, args.output,
                               login_customer_id=args.login_customer_id or "")
    except (ValueError, RuntimeError, OSError) as exc:
        return _err(str(exc))
    print(f"已建立 {path}（只有你自己可讀，已排除在版本控制之外）")
    return 0


def cmd_ads_ideas(args) -> int:
    from .google import ads as ads_mod

    project = Path(args.project)
    google = _site_google(project).get("google") or {}
    seeds = ([{"seed": args.seed, "geo": args.geo or "US", "lang": args.lang or "en", "url": args.url}]
             if args.seed or args.url else list(google.get("seeds") or []))
    if not seeds:
        return _err("請用 --seed 指定種子關鍵字，或在 site.yaml 的 google.seeds 設定")
    try:
        backend, customer = ads_mod.load_backend(args.config or google.get("ads_config") or "secrets/google-ads.yaml")
        planner = ads_mod.KeywordPlanner(backend, customer)
        rows = []
        for s in seeds:
            seed_list = [x for x in str(s.get("seed") or "").split("|") if x]
            geo = str(s.get("geo", "US")).upper()
            market = "tw" if geo == "TW" else "us"
            ideas = planner.ideas(seed_list, country=geo, language=str(s.get("lang", "en")), url=s.get("url"),
                                  limit=args.limit)
            got = ads_mod.ideas_to_rows(ideas, market=market, currency=planner.account_currency(),
                                        fx_to_usd=google.get("fx_to_usd") or {}, geo=geo, language=str(s.get("lang", "")))
            print(f"{geo}「{' | '.join(seed_list) or s.get('url')}」：取得 {len(got)} 個關鍵字")
            rows += got
    except ads_mod.AdsError as exc:
        return _err(str(exc))
    except Exception as exc:  # Google Ads API 的錯誤（權限、配額等）
        return _err(f"Google Ads API 回傳錯誤：{exc}")
    path = ads_mod.write_keywords_csv(rows, project / "keywords.csv", merge=not args.replace)
    print(f"已更新 {path}（資料來源：Google Ads Keyword Planner）")
    return 0


def cmd_opportunities(args) -> int:
    from .google.opportunities import rank_opportunities

    try:
        opps = rank_opportunities(args.project, brief_top=args.brief)
    except FileNotFoundError as exc:
        return _err(str(exc))
    print(f"{'#':>3} {'分數':>9} {'第3名月收益':>14}  {'訊號':<14} 關鍵字")
    for i, o in enumerate(opps[: args.top], 1):
        signals = " ".join(x for x in ("熱搜中" if o.trending else "", f"旺季{o.peak_month}月" if o.peak_month else "",
                                       "要趕快" if o.urgent else "", f"已有:{o.covered_by}" if o.covered_by else "") if x)
        print(f"{i:>3} {o.score:>9,.0f} {o.currency:>4} {o.forecast_total:>9,.0f}  {signals:<14} {o.term}")
        if o.brief_path:
            print(f"      → 已建立草稿 {o.brief_path}")
    return 0


def cmd_deploy(args) -> int:
    from .deploy import DeployError, deploy_site

    try:
        out = deploy_site(args.project)
    except DeployError as exc:
        return _err(str(exc))
    print(f"已部署 {out} 到 Cloudflare Pages")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="seoengine", description="雙軌 SEO 變現系統")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="建立新網站專案")
    s.add_argument("directory")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("keywords", help="關鍵字錢景排序")
    s.add_argument("csv")
    s.add_argument("--max-kd", type=int, default=None)
    s.add_argument("--min-volume", type=int, default=0)
    s.add_argument("--top", type=int, default=None)
    s.add_argument("--clusters", action="store_true")
    s.add_argument("--fx", action="append", metavar="幣別=匯率",
                   help="Google Ads 匯出檔的出價不是美元時，指定對美元匯率，例如 --fx TWD=0.0307")
    s.add_argument("--market", choices=["tw", "us"], help="規劃工具匯出檔沒有市場欄位；預設中文→tw、英文→us")
    s.set_defaults(func=cmd_keywords)

    s = sub.add_parser("forecast", help="雙幣別收益預估")
    s.add_argument("csv")
    s.add_argument("--position", type=float, default=3)
    s.add_argument("--fx", action="append", metavar="幣別=匯率",
                   help="Google Ads 匯出檔的出價不是美元時，指定對美元匯率，例如 --fx TWD=0.0307")
    s.add_argument("--market", choices=["tw", "us"], help="規劃工具匯出檔沒有市場欄位；預設中文→tw、英文→us")
    s.set_defaults(func=cmd_forecast)

    s = sub.add_parser("brief", help="產生文章骨架")
    s.add_argument("keyword")
    s.add_argument("--project", default=".")
    s.add_argument("--market", choices=["tw", "us"], default="tw")
    s.add_argument("--slug")
    s.set_defaults(func=cmd_brief)

    s = sub.add_parser("check", help="品質閘門")
    s.add_argument("project", nargs="?", default=".")
    s.add_argument("--include-drafts", action="store_true")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("build", help="建置網站")
    s.add_argument("project", nargs="?", default=".")
    s.add_argument("--out")
    s.add_argument("--force", action="store_true", help="連未通過品質閘門的文章也發布（不建議）")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("viz", help="產生動畫視覺化儀表板")
    s.add_argument("project", nargs="?", default=".")
    s.add_argument("--keywords", help="關鍵字 CSV（預設用網站資料夾的 keywords.csv 或 keywords.example.csv）")
    s.add_argument("-o", "--output", help="輸出路徑（預設 <網站>/dashboard/index.html）")
    s.set_defaults(func=cmd_viz)

    tr = sub.add_parser("trends", help="Google Trends：熱搜 RSS、Explore CSV、官方 API")
    tsub = tr.add_subparsers(dest="trends_cmd", required=True)
    s = tsub.add_parser("trending", help="抓 Google Trends 熱門搜尋（RSS）並依主題篩選")
    s.add_argument("--project", default=".")
    s.add_argument("--geo", help="國家代碼，逗號分隔（預設用 site.yaml 的 trends.geos）")
    s.add_argument("--include", help="主題關鍵字，逗號分隔（預設用 site.yaml 的 trends.include）")
    s.add_argument("--exclude")
    s.set_defaults(func=cmd_trends_trending)
    s = tsub.add_parser("import", help="匯入 Google Trends Explore 匯出的 CSV，計算旺季")
    s.add_argument("csv")
    s.add_argument("--project", default=".")
    s.set_defaults(func=cmd_trends_import)
    s = tsub.add_parser("api", help="官方 Google Trends API（alpha）")
    s.add_argument("keywords")
    s.add_argument("--geo", default="US")
    s.set_defaults(func=cmd_trends_api)

    ad = sub.add_parser("ads", help="Google Ads Keyword Planner")
    asub = ad.add_subparsers(dest="ads_cmd", required=True)
    s = asub.add_parser("auth", help="OAuth 授權並建立 google-ads.yaml")
    s.add_argument("--client-secrets", required=True, help="Google Cloud 下載的 OAuth 用戶端 JSON（桌面應用程式）")
    s.add_argument("--developer-token", help="選填：2026-09-09 起已停用，API 會忽略；權限改由 Cloud 專案的存取等級控管")
    s.add_argument("--customer-id", required=True, help="Google Ads 客戶 ID，例如 123-456-7890")
    s.add_argument("--login-customer-id", help="透過管理員帳戶存取時填管理員帳戶 ID")
    s.add_argument("-o", "--output", default="secrets/google-ads.yaml")
    s.set_defaults(func=cmd_ads_auth)
    s = asub.add_parser("ideas", help="用 Keyword Planner 取得真實搜尋量與出價，更新 keywords.csv")
    s.add_argument("--project", default=".")
    s.add_argument("--seed", help="種子關鍵字，多個用 | 分隔（不填則用 site.yaml 的 google.seeds）")
    s.add_argument("--url", help="用網址當種子")
    s.add_argument("--geo")
    s.add_argument("--lang")
    s.add_argument("--limit", type=int, default=200)
    s.add_argument("--config", help="google-ads.yaml 路徑（預設 secrets/google-ads.yaml）")
    s.add_argument("--replace", action="store_true", help="覆蓋整個 keywords.csv（預設合併）")
    s.set_defaults(func=cmd_ads_ideas)

    s = sub.add_parser("opportunities", help="合併 Ads 與 Trends 資料，排出流量機會")
    s.add_argument("--project", default=".")
    s.add_argument("--brief", type=int, default=0, help="為前 N 個新機會自動產生文章骨架")
    s.add_argument("--top", type=int, default=20)
    s.set_defaults(func=cmd_opportunities)

    s = sub.add_parser("deploy", help="建置並部署前端網站到 Cloudflare Pages（不含儀表板與金鑰）")
    s.add_argument("project", nargs="?", default=".")
    s.set_defaults(func=cmd_deploy)

    s = sub.add_parser("report", help="Search Console 優化週報")
    s.add_argument("--gsc", required=True)
    s.add_argument("--earnings")
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
