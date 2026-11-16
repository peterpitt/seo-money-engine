"""JSON-LD 結構化資料：Article / FAQPage / BreadcrumbList。"""
from __future__ import annotations

import json

from .content import Article


def _dump(data: dict) -> str:
    # 防止 </script> 斷開 JSON-LD
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def article_schema(article: Article, url: str, site_name: str, author: str | None = None,
                   author_url: str | None = None, author_type: str = "person") -> str:
    """author_type="organization"：站台署名是編輯團隊而不是個人時，結構化資料如實標成 Organization。
    文章自己有 author 欄位時一律視為個人署名。author_url 通常是「關於我們」頁。"""
    is_person = bool(article.author) or author_type != "organization"
    who = {"@type": "Person" if is_person else "Organization", "name": article.author or author or site_name}
    if author_url:
        who["url"] = author_url
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title,
        "description": article.description,
        "inLanguage": article.lang,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "datePublished": article.date.isoformat(),
        "dateModified": article.updated.isoformat(),
        "author": who,
        "publisher": {"@type": "Organization", "name": site_name},
    }
    if article.image:
        data["image"] = [article.image]
    return _dump(data)


def faq_schema(faq: list[dict]) -> str | None:
    if not faq:
        return None
    return _dump({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
            for item in faq
        ],
    })


def breadcrumb_schema(items: list[tuple[str, str]]) -> str:
    return _dump({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": url}
            for i, (name, url) in enumerate(items, start=1)
        ],
    })
