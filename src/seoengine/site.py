"""靜態網站建置：品質閘門 → 變現 → 內部連結 → 結構化資料 → sitemap / RSS / robots / ads.txt。"""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .calendar import CalendarError, expand_calendar_shortcodes, load_calendars
from .calendar_page import LANGUAGES, CalendarPageConfig, load_i18n, page_path, render_calendar_page
from .content import Article, ContentError, extract_headings, load_articles, render_markdown
from .linking import LinkTarget, auto_internal_links
from .monetize import (
    AdConfig,
    MonetizeError,
    ads_txt,
    disclosure_html,
    expand_shortcodes,
    inject_ads,
    load_offers,
    redirect_page,
)
from .quality import QualityConfig, QualityReport, check_article
from .schema import article_schema, breadcrumb_schema, faq_schema
from .text import tokens

BUILD_MARKER = ".seoengine-build"
# Cloudflare Pages 的 _headers：安全標頭＋靜態檔案快取（style.css / timeline.js 每次建置內容可能改變，所以只快取 1 天）
CLOUDFLARE_HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/style.css
  Cache-Control: public, max-age=86400

/timeline.js
  Cache-Control: public, max-age=86400

/go/*
  X-Robots-Tag: noindex, nofollow
"""
TEMPLATES = Path(__file__).parent / "templates"


class BuildError(RuntimeError):
    pass


@dataclass
class SiteConfig:
    name: str
    base_url: str
    default_lang: str = "zh-TW"
    author: str = ""
    author_type: str = "person"      # person｜organization：站台署名是個人還是編輯團隊（影響結構化資料的作者型別）
    description: str = ""
    contact_email: str = ""
    out_dir: str = "public"
    max_internal_links: int = 3
    ga4: str = ""
    adsense: AdConfig = field(default_factory=AdConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    calendar_page: CalendarPageConfig | None = None
    network: list[tuple[str, str]] = field(default_factory=list)   # 同品牌的其他網站（主網域、子網域）

    @property
    def sister_sites(self) -> list[tuple[str, str]]:
        """頁尾要連的姊妹站：network 裡除了自己以外的網站。"""
        return [(n, u) for n, u in self.network if u != self.base_url]

    def about_path(self, lang: str) -> str:
        """「關於我們」頁：文章署名與結構化資料的作者網址都連到這裡。"""
        return "/about/zh-tw/" if lang.lower().startswith("zh") else "/about/"

    def calendar_nav(self, lang: str) -> tuple[str, str] | None:
        """文章頁首的「假日行事曆」連結：優先連到同語言版本。"""
        cp = self.calendar_page
        if not cp:
            return None
        default = cp.default_lang(self.default_lang)
        target = lang if lang in cp.languages else default
        return page_path(target, default), LANGUAGES[target]["nav"]

    @classmethod
    def load(cls, path: str | Path) -> "SiteConfig":
        path = Path(path)
        if not path.exists():
            raise BuildError(f"找不到設定檔 {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        site = data.get("site") or {}
        base_url = str(site.get("base_url") or "").rstrip("/")
        if not base_url.startswith(("https://", "http://")):
            raise BuildError("site.base_url 必須是完整網址，例如 https://example.com")
        author_type = str(site.get("author_type") or "person").strip().lower()
        if author_type not in ("person", "organization"):
            raise BuildError(f"site.author_type 只能是 person 或 organization，收到 {author_type!r}")
        return cls(
            name=str(site.get("name") or "My Site"),
            base_url=base_url,
            default_lang=str(site.get("default_lang") or "zh-TW"),
            author=str(site.get("author") or ""),
            author_type=author_type,
            description=str(site.get("description") or ""),
            contact_email=str(site.get("contact_email") or ""),
            out_dir=str(site.get("out_dir") or "public"),
            max_internal_links=int(site.get("max_internal_links", 3)),
            ga4=str((data.get("analytics") or {}).get("ga4") or ""),
            adsense=AdConfig.from_mapping(data.get("adsense")),
            quality=QualityConfig.from_mapping(data.get("quality")),
            calendar_page=_calendar_page(data.get("calendar_page")),
            network=_network(site.get("network")),
        )


def _network(items) -> list[tuple[str, str]]:
    out = []
    for item in items or []:
        name, url = str(item.get("name") or "").strip(), str(item.get("url") or "").strip().rstrip("/")
        if not name or not url.startswith("https://"):
            raise BuildError(f"site.network 每一項要有 name 與 https:// 開頭的 url，收到 {item!r}")
        out.append((name, url))
    return out


def _calendar_page(data) -> CalendarPageConfig | None:
    try:
        return CalendarPageConfig.from_mapping(data)
    except ValueError as exc:
        raise BuildError(f"site.yaml calendar_page: {exc}") from exc


@dataclass
class BuildResult:
    out_dir: Path
    published: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    reports: dict[str, QualityReport] = field(default_factory=dict)


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["asset_v"] = _asset_version()
    return env


def _asset_version() -> str:
    """style.css 的內容雜湊，當成網址版本號：CSS 一變網址就變，瀏覽器／CDN 不會再送到舊的那份。"""
    return hashlib.sha1((TEMPLATES / "style.css").read_bytes()).hexdigest()[:8]


def _prepare_out_dir(out: Path) -> None:
    """只清除由本工具產生過的資料夾，避免誤刪使用者檔案。"""
    if out.exists():
        if any(out.iterdir()) and not (out / BUILD_MARKER).exists():
            raise BuildError(f"輸出資料夾 {out} 已有其他檔案且不是 seoengine 產生的，拒絕覆蓋")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / BUILD_MARKER).write_text("generated by seoengine\n", encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _related(article: Article, pool: list[Article], limit: int = 3) -> list[Article]:
    base = tokens(article.keyword + " " + article.title)
    scored = []
    for other in pool:
        if other.slug == article.slug or other.lang != article.lang:
            continue
        overlap = len(base & tokens(other.keyword + " " + other.title))
        scored.append((overlap, other.updated, other))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [a for _, _, a in scored[:limit]]


def build_site(project_dir: str | Path, out_dir: str | Path | None = None, force: bool = False,
               today: dt.date | None = None) -> BuildResult:
    """today：建置當天（預設今天）。「剩餘假日」與行事曆倒數以這天為準。"""
    project = Path(project_dir)
    today = today or dt.date.today()
    cfg = SiteConfig.load(project / "site.yaml")
    try:
        offers = load_offers(project / "offers.yaml")
        calendars = load_calendars(project)
        articles = [a for a in load_articles(project / "content") if not a.draft]
    except (ContentError, ValueError) as exc:
        raise BuildError(str(exc)) from exc

    seen: dict[str, str] = {}
    for a in articles:
        if a.slug in seen:
            raise BuildError(f"duplicate slug '{a.slug}' in {seen[a.slug]} and {a.source}")
        seen[a.slug] = a.source

    out = Path(out_dir) if out_dir else project / cfg.out_dir
    result = BuildResult(out_dir=out)

    expanded: dict[str, tuple[str, set[str]]] = {}
    for a in articles:
        try:
            body_md = expand_calendar_shortcodes(a.body_md, calendars, a.lang, today=today)
            expanded[a.slug] = expand_shortcodes(body_md, offers, lang=a.lang)
        except (MonetizeError, CalendarError) as exc:
            raise BuildError(f"{a.source}: {exc}") from exc
        report = check_article(a, offers, cfg.quality)
        result.reports[a.slug] = report
        if report.passed or force:
            result.published.append(a.slug)
        else:
            rules = ", ".join(sorted({i.rule for i in report.errors}))
            result.skipped[a.slug] = f"quality gate failed: {rules}"

    published = sorted((a for a in articles if a.slug in result.published), key=lambda a: a.date, reverse=True)
    _prepare_out_dir(out)

    env = _env()
    url_of = lambda a: f"{cfg.base_url}/{a.slug}/"  # noqa: E731
    by_translation: dict[str, list[Article]] = {}
    for a in published:
        if a.translation_key:
            by_translation.setdefault(a.translation_key, []).append(a)

    used_offers: set[str] = set()
    article_tpl = env.get_template("article.html")
    for a in published:
        md_text, used = expanded[a.slug]
        used_offers |= used
        body = render_markdown(md_text)
        targets = [LinkTarget(o.keyword, f"/{o.slug}/", o.slug) for o in published if o.lang == a.lang]
        body, _ = auto_internal_links(body, a.slug, targets, cfg.max_internal_links)
        body = inject_ads(body, cfg.adsense)

        alternates = []
        group = by_translation.get(a.translation_key or "", [])
        if len(group) > 1:
            alternates = [(o.lang, url_of(o)) for o in group]
            default = next((o for o in group if o.lang == cfg.default_lang), group[0])
            alternates.append(("x-default", url_of(default)))

        schemas = [
            article_schema(a, url_of(a), cfg.name, cfg.author,
                           author_url=cfg.base_url + cfg.about_path(a.lang), author_type=cfg.author_type),
            breadcrumb_schema([(cfg.name, cfg.base_url + "/"), (a.title, url_of(a))]),
        ]
        if a.faq:
            schemas.append(faq_schema(a.faq))

        page = article_tpl.render(
            site=cfg,
            article=a,
            canonical=url_of(a),
            body=body,
            toc=[(hid, text) for lvl, hid, text in extract_headings(body) if lvl == 2],
            disclosure=disclosure_html(a.lang) if used else "",
            alternates=alternates,
            schemas=schemas,
            related=_related(a, published),
            nav_link=cfg.calendar_nav(a.lang),
            about_href=cfg.about_path(a.lang),
        )
        _write(out / a.slug / "index.html", page)

    for oid in sorted(used_offers):
        _write(out / "go" / oid / "index.html", redirect_page(offers[oid]))

    extra_urls: list[str] = []
    home_is_calendar = bool(cfg.calendar_page and calendars)
    if home_is_calendar:
        i18n = load_i18n(project)
        default = cfg.calendar_page.default_lang(cfg.default_lang)
        articles_url = "/articles/" if published else None
        for lang in cfg.calendar_page.languages:
            try:
                page = render_calendar_page(cfg.name, cfg.base_url, calendars, i18n, lang,
                                            cfg.calendar_page, today=today, site=cfg, nav_to=articles_url)
            except ValueError as exc:
                raise BuildError(str(exc)) from exc
            path = page_path(lang, default)
            _write(out / path.strip("/") / "index.html", page)
            if path != "/":
                extra_urls.append(cfg.base_url + path)
        # 舊的 /calendar/ 預設頁已移到首頁；保留 301 轉址，既有連結與書籤不會 404
        _write(out / "_redirects", "/calendar/ / 301\n")

    privacy_updated = max((a.updated for a in published), default=dt.date.today()).isoformat()
    legal_pages = (
        ("privacy", "privacy.html"),
        ("about", "about.html"),
        ("contact", "contact.html"),
        ("terms", "terms.html"),
    )
    for slug, template_name in legal_pages:
        template = env.get_template(template_name)
        for lang, path in (("en", f"/{slug}/"), ("zh-TW", f"/{slug}/zh-tw/")):
            _write(out / path.strip("/") / "index.html", template.render(
                site=cfg, page_lang=lang, canonical=cfg.base_url + path, updated=privacy_updated,
                contact=cfg.contact_email, nav_link=cfg.calendar_nav(lang)))
            extra_urls.append(cfg.base_url + path)

    langs = sorted({a.lang for a in published}, key=lambda l: (l != cfg.default_lang, l))
    article_index = env.get_template("index.html").render(
        site=cfg, canonical=cfg.base_url + ("/articles/" if home_is_calendar else "/"),
        sections=[(lang, [a for a in published if a.lang == lang]) for lang in langs],
        nav_link=cfg.calendar_nav(cfg.default_lang),
    )
    if home_is_calendar:
        # 首頁已是行事曆；文章清單改放 /articles/（文章樞紐頁，保留內部連結與 SEO）
        if published:
            _write(out / "articles" / "index.html", article_index)
            extra_urls.append(cfg.base_url + "/articles/")
    else:
        _write(out / "index.html", article_index)
    _write(out / "404.html", env.get_template("404.html").render(site=cfg, canonical=cfg.base_url + "/404.html"))
    shutil.copyfile(TEMPLATES / "style.css", out / "style.css")
    shutil.copyfile(TEMPLATES / "timeline.js", out / "timeline.js")
    _write(out / "_headers", CLOUDFLARE_HEADERS)

    _write(out / "sitemap.xml", _sitemap(cfg, published, extra_urls))
    _write(out / "feed.xml", _feed(cfg, published))
    _write(
        out / "robots.txt",
        f"User-agent: *\nAllow: /\nDisallow: /go/\n\nSitemap: {cfg.base_url}/sitemap.xml\n",
    )
    if txt := ads_txt(cfg.adsense.client):
        _write(out / "ads.txt", txt)

    (project / "quality-report.json").write_text(
        json.dumps({slug: r.to_dict() for slug, r in result.reports.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _sitemap(cfg: SiteConfig, articles: list[Article], extra_urls: list[str] | None = None) -> str:
    today = max((a.updated for a in articles), default=dt.date.today())
    entries = [(cfg.base_url + "/", today)] + [(u, dt.date.today()) for u in extra_urls or []]
    entries += [(f"{cfg.base_url}/{a.slug}/", a.updated) for a in articles]
    urls = "".join(
        f"  <url><loc>{xml_escape(loc)}</loc><lastmod>{lastmod.isoformat()}</lastmod></url>\n"
        for loc, lastmod in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def _rfc822(day: dt.date) -> str:
    return email.utils.format_datetime(dt.datetime(day.year, day.month, day.day, 8, 0, tzinfo=dt.timezone.utc))


def _feed(cfg: SiteConfig, articles: list[Article]) -> str:
    items = "".join(
        "    <item>\n"
        f"      <title>{xml_escape(a.title)}</title>\n"
        f"      <link>{cfg.base_url}/{a.slug}/</link>\n"
        f'      <guid isPermaLink="true">{cfg.base_url}/{a.slug}/</guid>\n'
        f"      <pubDate>{_rfc822(a.date)}</pubDate>\n"
        f"      <description>{xml_escape(a.description)}</description>\n"
        "    </item>\n"
        for a in articles[:50]
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
        f"    <title>{xml_escape(cfg.name)}</title>\n"
        f"    <link>{cfg.base_url}/</link>\n"
        f"    <description>{xml_escape(cfg.description or cfg.name)}</description>\n"
        f"    <language>{xml_escape(cfg.default_lang)}</language>\n"
        f"{items}  </channel>\n</rss>\n"
    )
