"""變現元件：聯盟短碼、CTA、比較表、跳轉頁、AdSense 版位與 ads.txt。

短碼語法（寫在 Markdown 內）：
  [[offer:id]]              文內聯盟連結（顯示商品名）
  [[offer:id|自訂文字]]      文內聯盟連結（自訂錨點文字）
  [[cta:id]]                行動呼籲卡片
  [[compare:id1,id2,id3]]   商品比較表
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import yaml

from .text import strip_html, word_count

AD_MARKER = "<!-- [AdSense 高轉換版位建議：回應式內文廣告] -->"
_OFFER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SHORTCODE = re.compile(r"\[\[(offer|cta|compare):([^\]|]+)(?:\|([^\]]+))?\]\]")
_H2_SPLIT = re.compile(r"(?=<h2[\s>])")


class MonetizeError(ValueError):
    pass


@dataclass
class Offer:
    id: str
    name: str
    url: str
    network: str = ""
    market: str = ""
    commission: str = ""
    price: str = ""
    rating: float | None = None
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    best_for: str = ""
    cta: str = ""

    def __post_init__(self) -> None:
        if not _OFFER_ID.match(self.id):
            raise ValueError(f"offer id {self.id!r} must be lowercase letters, digits, - or _")
        if not re.match(r"^https?://", self.url):
            raise ValueError(f"offer {self.id}: url must start with http:// or https://")

    @property
    def placeholder(self) -> bool:
        """連結還是 example.com 這類範例網址：不產生按鈕與跳轉頁，換成真實聯盟網址後自動出現。"""
        from .domains import is_placeholder_url

        return is_placeholder_url(self.url)

    @property
    def go_url(self) -> str:
        return f"/go/{self.id}/"


def load_offers(path: str | Path) -> dict[str, Offer]:
    path = Path(path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    offers = {}
    for oid, fields in data.items():
        fields = dict(fields or {})
        fields["pros"] = list(fields.get("pros") or [])
        fields["cons"] = list(fields.get("cons") or [])
        offers[str(oid)] = Offer(id=str(oid), **fields)
    return offers


def _link(offer: Offer, text: str, css: str = "aff-link") -> str:
    return (
        f'<a href="{offer.go_url}" rel="sponsored nofollow noopener" target="_blank" '
        f'class="{css}" data-offer="{offer.id}">{html.escape(text)}</a>'
    )


def _stars(rating: float | None) -> str:
    return f"★ {rating:.1f}/5" if rating is not None else ""


_LABELS = {
    "zh": {"product": "商品", "price": "價格", "rating": "評分", "pros": "優點", "cons": "缺點",
           "cta": "查看最新價格", "cta_short": "查看價格"},
    "en": {"product": "Product", "price": "Price", "rating": "Rating", "pros": "Pros", "cons": "Cons",
           "cta": "Check price", "cta_short": "Check price"},
}


def _labels(lang: str) -> dict[str, str]:
    return _LABELS["zh" if lang.lower().startswith("zh") else "en"]


def _cta_box(offer: Offer, lang: str) -> str:
    e = html.escape
    meta = " · ".join(x for x in (e(offer.price), _stars(offer.rating), e(offer.best_for)) if x)
    pros = "".join(f"<li>{e(p)}</li>" for p in offer.pros[:3])
    return (
        f'<div class="cta-box" data-offer="{offer.id}">'
        f'<p class="cta-title">{e(offer.name)}</p>'
        + (f'<p class="cta-meta">{meta}</p>' if meta else "")
        + (f'<ul class="cta-pros">{pros}</ul>' if pros else "")
        + _link(offer, offer.cta or _labels(lang)["cta"], css="cta-button")
        + "</div>"
    )


def _compare_table(offers: list[Offer], lang: str) -> str:
    e, t = html.escape, _labels(lang)
    rows = []
    for o in offers:
        rows.append(
            "<tr>"
            f'<td class="cmp-name" data-label="{t["product"]}">{e(o.name)}</td>'
            f'<td data-label="{t["price"]}">{e(o.price) or "—"}</td>'
            f'<td data-label="{t["rating"]}">{_stars(o.rating) or "—"}</td>'
            f'<td data-label="{t["pros"]}">{"<br>".join(e(p) for p in o.pros) or "—"}</td>'
            f'<td data-label="{t["cons"]}">{"<br>".join(e(c) for c in o.cons) or "—"}</td>'
            f'<td class="cmp-action">{_link(o, o.cta or t["cta_short"], css="cmp-button")}</td>'
            "</tr>"
        )
    head = "".join(f"<th>{t[k]}</th>" for k in ("product", "price", "rating", "pros", "cons"))
    return (
        '<div class="compare-wrap"><table class="compare-table">'
        f"<thead><tr>{head}<th></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def expand_shortcodes(md_text: str, offers: Mapping[str, Offer], lang: str = "zh-TW") -> tuple[str, set[str]]:
    used: set[str] = set()

    def get(oid: str) -> Offer:
        oid = oid.strip()
        if oid not in offers:
            raise MonetizeError(f"unknown offer id '{oid}' (add it to offers.yaml)")
        used.add(oid)
        return offers[oid]

    def known(oid: str) -> Offer:
        oid = oid.strip()
        if oid not in offers:
            raise MonetizeError(f"unknown offer id '{oid}' (add it to offers.yaml)")
        return offers[oid]

    def replace(m: re.Match) -> str:
        kind, arg, label = m.group(1), m.group(2), m.group(3)
        if kind == "offer":
            offer = known(arg)
            text = (label or offer.name).strip()
            return text if offer.placeholder else _link(get(arg), text)   # 範例網址：只留文字、不放連結
        if kind == "cta":
            offer = known(arg)
            return "" if offer.placeholder else "\n\n" + _cta_box(get(arg), lang) + "\n\n"
        live = [get(i) for i in arg.split(",") if i.strip() and not known(i).placeholder]
        return "\n\n" + _compare_table(live, lang) + "\n\n" if live else ""

    return _SHORTCODE.sub(replace, md_text), used


def disclosure_html(lang: str) -> str:
    if lang.lower().startswith("zh"):
        text = "揭露聲明：本文含有聯盟行銷連結，透過連結購買我們可能獲得分潤，你不需多付任何費用，評測內容不受廠商影響。"
    else:
        text = ("Disclosure: this article contains affiliate links. If you buy through them we may earn a "
                "commission at no extra cost to you. Our reviews are independent.")
    return f'<p class="affiliate-disclosure">{text}</p>'


def redirect_page(offer: Offer) -> str:
    url_attr = html.escape(offer.url, quote=True)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        '<meta name="robots" content="noindex, nofollow">'
        f'<meta http-equiv="refresh" content="0; url={url_attr}">'
        f"<title>{html.escape(offer.name)}</title>"
        f"<script>location.replace({json.dumps(offer.url)});</script>"
        f'</head><body><p><a href="{url_attr}" rel="sponsored nofollow">前往 {html.escape(offer.name)}</a></p></body></html>\n'
    )


@dataclass(frozen=True)
class AdConfig:
    client: str = ""
    slot: str = ""
    max_ads: int = 3
    min_words_between: int = 250

    @property
    def enabled(self) -> bool:
        return self.client.startswith("ca-pub-")

    @classmethod
    def from_mapping(cls, data: Mapping | None) -> "AdConfig":
        data = dict(data or {})
        return cls(
            client=str(data.get("client") or ""),
            slot=str(data.get("slot") or ""),
            max_ads=int(data.get("max_ads", 3)),
            min_words_between=int(data.get("min_words_between", 250)),
        )


def ad_unit(cfg: AdConfig) -> str:
    if not cfg.enabled:
        return AD_MARKER
    return (
        '<div class="ad-slot">\n'
        f"{AD_MARKER}\n"
        f'<ins class="adsbygoogle" style="display:block" data-ad-client="{html.escape(cfg.client)}" '
        f'data-ad-slot="{html.escape(cfg.slot)}" data-ad-format="auto" data-full-width-responsive="true"></ins>\n'
        "<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n"
        "</div>"
    )


def inject_ads(html_text: str, cfg: AdConfig) -> str:
    """在 H2 之前插入廣告（讀者剛讀完一段、注意力轉換的位置），控制數量與間距。"""
    segments = _H2_SPLIT.split(html_text)
    out = [segments[0]]
    words_since, placed = word_count(strip_html(segments[0])), 0
    for seg in segments[1:]:
        if placed < cfg.max_ads and words_since >= cfg.min_words_between:
            out.append(ad_unit(cfg) + "\n")
            placed += 1
            words_since = 0
        out.append(seg)
        words_since += word_count(strip_html(seg))
    return "".join(out)


def ads_txt(client: str) -> str | None:
    if not client.startswith("ca-pub-"):
        return None
    return f"google.com, {client.removeprefix('ca-')}, DIRECT, f08c47fec0942fa0\n"
