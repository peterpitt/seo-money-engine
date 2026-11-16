"""依搜尋意圖產生文章骨架（draft）。CLI 的 brief 與流量機會的自動產生共用。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from .keywords import Intent, Keyword
from .text import slugify

_OUTLINES = {
    ("zh", Intent.COMMERCIAL): [
        "{kw}快速結論：先看這張比較表",
        "挑選前必看的 5 個重點",
        "實測比較：我怎麼測、結果如何",
        "依預算與使用情境推薦",
        "常見踩雷與售後注意事項",
    ],
    ("zh", Intent.TRANSACTIONAL): [
        "目前最划算的入手方式",
        "各通路價格與優惠比較",
        "購買前的檢查清單",
        "保固與退換貨重點",
    ],
    ("zh", Intent.INFORMATIONAL): [
        "{kw}是什麼？一分鐘看懂",
        "步驟教學：照著做就會",
        "新手最常犯的錯",
        "進階技巧與工具推薦",
    ],
    ("en", Intent.COMMERCIAL): [
        "Quick verdict: the comparison table",
        "What actually matters when choosing",
        "How I tested and what I found",
        "Best picks by budget and use case",
        "Mistakes to avoid",
    ],
    ("en", Intent.TRANSACTIONAL): [
        "Where to get the best price right now",
        "Price and deal comparison",
        "Pre-purchase checklist",
        "Warranty and returns",
    ],
    ("en", Intent.INFORMATIONAL): [
        "What is {kw}? The short answer",
        "Step-by-step guide",
        "Common mistakes",
        "Advanced tips and tools",
    ],
}



def create_brief(project: Path, keyword: str, market: str = "tw", slug: str | None = None) -> tuple[Path, Intent]:
    """建立 content/<slug>.md 草稿；檔案已存在時丟出 FileExistsError（不覆蓋使用者的文章）。"""
    lang = "en" if market == "us" else "zh-TW"
    lang_key = "en" if lang == "en" else "zh"
    kw = Keyword(keyword, 0, 0, 0, market=market)
    intent = Intent.COMMERCIAL if kw.intent is Intent.NAVIGATIONAL else kw.intent
    slug = slug or slugify(keyword)
    path = Path(project) / "content" / f"{slug}.md"
    if path.exists():
        raise FileExistsError(str(path))

    if lang_key == "zh":
        title = f"{keyword}｜{dt.date.today().year} 實測整理"
        intro = (f"<!-- 第一段：用一兩句話直接回答「{keyword}」，並說明你的實際經驗（用了多久、測了什麼）。 -->\n\n"
                 f"{keyword}……")
        note = "<!-- 寫下你自己的測試數據、照片（記得 alt 文字）、優缺點。可用 [[cta:商品id]] 或 [[compare:a,b,c]] 插入變現元件。 -->"
    else:
        title = f"{keyword.title()} ({dt.date.today().year}): Tested and Ranked"
        intro = (f"<!-- Intro: answer '{keyword}' in 1-2 sentences and state your hands-on experience. -->\n\n"
                 f"{keyword}…")
        note = "<!-- Add your own test data, photos (with alt text), pros/cons. Use [[cta:id]] or [[compare:a,b,c]]. -->"

    meta = {
        "title": title,
        "slug": slug,
        "keyword": keyword,
        "description": "",
        "lang": lang,
        "market": market,
        "date": dt.date.today().isoformat(),
        "draft": True,
        "faq": [{"q": "TODO", "a": "TODO"}],
    }
    sections = "\n\n".join(f"## {h.format(kw=keyword)}\n\n{note}"
                           for h in _OUTLINES[(lang_key, intent)])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n"
        + intro + "\n\n" + sections + "\n",
        encoding="utf-8",
    )
    return path, intent


