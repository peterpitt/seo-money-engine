"""測試用的文章與專案產生器（只在測試中使用）。"""
from __future__ import annotations

from pathlib import Path

import yaml

ZH_SENTENCES = [
    "研磨的均勻度會直接影響萃取的穩定性，所以挑選時要先看刀盤結構。",
    "我實際用同一支豆子比較了三種刻度，細粉越少，杯中的雜味就越低。",
    "手搖款適合一天一到兩杯的人，電動款則適合需要連續出杯的家庭。",
    "清潔頻率建議每兩週一次，用毛刷清掉卡在刀盤縫隙的咖啡粉即可。",
]

EN_SENTENCES = [
    "Grind consistency drives extraction, so burr geometry matters more than motor power.",
    "I brewed the same beans at three settings and fewer fines meant a cleaner cup.",
    "A hand grinder suits one or two cups a day, while an electric model suits busy households.",
    "Brush the burrs every two weeks so old grounds do not turn stale and bitter.",
]


def _blocks(*blocks: str) -> str:
    return "\n\n".join(b for b in blocks if b) + "\n"


def zh_body(keyword: str, extra: str = "", mention: str | None = None) -> str:
    s = ZH_SENTENCES
    return _blocks(
        f"{keyword}之前，先搞清楚自己一天喝幾杯、用什麼方式沖煮，選擇會簡單很多。",
        "## 刀盤結構怎麼選",
        s[0] + s[1],
        s[2] + s[3],
        "## 實際使用心得",
        s[1] + s[0],
        s[3] + s[2],
        f"如果你還在挑器材，可以先看{mention}整理的重點。" if mention else "",
        extra,
    )


def en_body(keyword: str, extra: str = "") -> str:
    s = EN_SENTENCES
    return _blocks(
        f"Picking the {keyword} starts with how many cups you brew a day and which method you use.",
        "## How burr design changes the cup",
        f"{s[0]} {s[1]}",
        f"{s[2]} {s[3]}",
        "## What I learned after a month of testing",
        f"{s[1]} {s[0]}",
        f"{s[3]} {s[2]}",
        extra,
    )


def article_md(
    slug: str,
    keyword: str,
    *,
    lang: str = "zh-TW",
    title: str | None = None,
    body: str | None = None,
    extra: str = "",
    faq: int = 0,
    draft: bool = False,
    translation_key: str | None = None,
    mention: str | None = None,
) -> str:
    if lang.startswith("zh"):
        title = title or f"{keyword}：2026 實測挑選指南"
        description = (
            f"整理{keyword}的實測心得：刀盤結構、刻度調整、清潔保養與預算分級，"
            "幫你用最少的錢買到適合自己的器材。"
        )
        body = body if body is not None else zh_body(keyword, extra, mention)
        market = "tw"
    else:
        title = title or f"{keyword.title()}: Tested Picks for 2026"
        description = (
            f"Hands-on notes on the {keyword}: burr design, grind settings, cleaning "
            "and budget tiers, so you buy once and brew better coffee."
        )
        body = body if body is not None else en_body(keyword, extra)
        market = "us"
    meta = {
        "title": title,
        "slug": slug,
        "keyword": keyword,
        "description": description,
        "lang": lang,
        "market": market,
        "date": "2026-10-01",
        "draft": draft,
    }
    if translation_key:
        meta["translation_key"] = translation_key
    if faq:
        meta["faq"] = [
            {"q": f"問題 {i + 1}：{keyword}要注意什麼？", "a": f"答案 {i + 1}：先確認預算與使用頻率。"}
            for i in range(faq)
        ]
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    return f"---\n{front}---\n\n{body}"


def write_project(root: Path, base_url: str = "https://coffee.example.com", **overrides) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "content").mkdir(exist_ok=True)
    config = {
        "site": {
            "name": "咖啡器材研究室",
            "base_url": base_url,
            "default_lang": "zh-TW",
            "author": "Tsung",
        },
        "adsense": {"client": "", "slot": "", "max_ads": 3, "min_words_between": 80},
        "quality": {"min_words": 120},
    }
    for key, value in overrides.items():
        config.setdefault(key, {}).update(value)
    (root / "site.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return root
