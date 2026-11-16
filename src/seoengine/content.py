"""文章載入：Markdown + YAML front matter。"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import markdown
import yaml
from markdown.extensions.toc import slugify_unicode

from .text import slugify

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
_HEADING = re.compile(r'<h([2-6]) id="([^"]+)">(.*?)</h\1>', re.S)


class ContentError(ValueError):
    pass


@dataclass
class Article:
    slug: str
    title: str
    keyword: str
    body_md: str
    description: str = ""
    lang: str = "zh-TW"
    market: str = "tw"
    date: dt.date = field(default_factory=dt.date.today)
    updated: dt.date | None = None
    draft: bool = False
    faq: list[dict] = field(default_factory=list)
    translation_key: str | None = None
    author: str | None = None
    category: str | None = None
    image: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.updated is None:
            self.updated = self.date


def _to_date(value, field_name: str, source: str) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise ContentError(f"{source}: invalid {field_name} {value!r} (use YYYY-MM-DD)") from exc


def parse_article(text: str, source: str = "<string>") -> Article:
    match = _FRONT.match(text.lstrip("﻿"))
    if not match:
        raise ContentError(f"{source}: missing YAML front matter (--- ... ---)")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"{source}: invalid front matter: {exc}") from exc
    if not isinstance(meta, dict):
        raise ContentError(f"{source}: front matter must be a mapping")
    for required in ("title", "keyword"):
        if not str(meta.get(required) or "").strip():
            raise ContentError(f"{source}: missing required field '{required}'")

    keyword = str(meta["keyword"]).strip()
    title = str(meta["title"]).strip()
    slug = str(meta.get("slug") or slugify(keyword) or slugify(title)).strip()
    if not SLUG_RE.match(slug):
        raise ContentError(f"{source}: slug {slug!r} must be lowercase letters, digits and hyphens")

    lang = str(meta.get("lang") or "zh-TW")
    market = str(meta.get("market") or ("tw" if lang.lower().startswith("zh") else "us")).lower()
    faq = meta.get("faq") or []
    if not isinstance(faq, list) or not all(isinstance(i, dict) and {"q", "a"} <= set(i) for i in faq):
        raise ContentError(f"{source}: faq must be a list of {{q, a}} items")

    date = _to_date(meta.get("date"), "date", source) or dt.date.today()
    return Article(
        slug=slug,
        title=title,
        keyword=keyword,
        body_md=match.group(2),
        description=str(meta.get("description") or "").strip(),
        lang=lang,
        market=market,
        date=date,
        updated=_to_date(meta.get("updated"), "updated", source) or date,
        draft=bool(meta.get("draft", False)),
        faq=[{"q": str(i["q"]), "a": str(i["a"])} for i in faq],
        translation_key=(str(meta["translation_key"]) if meta.get("translation_key") else None),
        author=meta.get("author"),
        category=meta.get("category"),
        image=meta.get("image"),
        source=source,
    )


def load_articles(directory: str | Path) -> list[Article]:
    """載入資料夾內所有 .md（底線開頭的檔案視為範本，略過）。"""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return [
        parse_article(p.read_text(encoding="utf-8"), source=str(p))
        for p in sorted(directory.glob("*.md"))
        if not p.name.startswith("_")
    ]


def render_markdown(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"],
        extension_configs={"toc": {"slugify": slugify_unicode, "toc_depth": "2-3"}},
        output_format="html",
    )


def extract_headings(html_text: str) -> list[tuple[int, str, str]]:
    from .text import strip_html

    return [(int(lvl), hid, strip_html(inner)) for lvl, hid, inner in _HEADING.findall(html_text)]
