"""自動內部連結：把站內其他文章的目標關鍵字，第一次出現時連過去。"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Sequence

from .text import is_latin

_SKIP_TAGS = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "script", "style", "code", "pre", "button", "th"}
_TAG = re.compile(r"(<[^>]+>)")
_TAG_NAME = re.compile(r"^<\s*(/)?\s*([a-zA-Z0-9]+)")


@dataclass(frozen=True)
class LinkTarget:
    keyword: str
    url: str
    slug: str


def _pattern(keyword: str) -> re.Pattern:
    body = r"\s+".join(re.escape(html.escape(p, quote=False)) for p in keyword.split())
    if is_latin(keyword):
        return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)
    return re.compile(body)


def auto_internal_links(
    html_text: str, current_slug: str, targets: Sequence[LinkTarget], max_links: int = 3
) -> tuple[str, list[str]]:
    pending = sorted(
        (t for t in targets if t.slug != current_slug and t.keyword.strip()),
        key=lambda t: -len(t.keyword),
    )
    patterns = {t.slug: _pattern(t.keyword) for t in pending}
    linked: list[str] = []
    skip_depth = 0
    out: list[str] = []

    for piece in _TAG.split(html_text):
        if piece.startswith("<"):
            m = _TAG_NAME.match(piece)
            if m and m.group(2).lower() in _SKIP_TAGS and not piece.endswith("/>"):
                skip_depth += -1 if m.group(1) else 1
                skip_depth = max(skip_depth, 0)
            out.append(piece)
            continue
        if skip_depth or not piece.strip() or len(linked) >= max_links:
            out.append(piece)
            continue

        parts: list[str | tuple[str]] = [piece]  # tuple = 已轉成連結的片段
        for target in pending:
            if target.slug in linked or len(linked) >= max_links:
                continue
            for idx, part in enumerate(parts):
                if isinstance(part, tuple):
                    continue
                m = patterns[target.slug].search(part)
                if m:
                    anchor = f'<a href="{html.escape(target.url)}">{m.group(0)}</a>'
                    parts[idx : idx + 1] = [part[: m.start()], (anchor,), part[m.end() :]]
                    linked.append(target.slug)
                    break
        out.append("".join(p[0] if isinstance(p, tuple) else p for p in parts))

    return "".join(out), linked
