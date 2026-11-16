"""內容品質閘門：擋下薄內容、AI 套話與基本 SEO 錯誤，避免拖累整站 E-E-A-T。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

from .content import Article, render_markdown
from .text import display_width, strip_html, word_count

AI_FILLER_PHRASES = (
    # 繁中
    "在這個日新月異的時代", "隨著科技的發展", "隨著科技的進步", "在當今社會", "在現今社會",
    "眾所周知", "不可否認", "總而言之，", "綜上所述", "值得注意的是", "讓我們一起來探討",
    "在這篇文章中，我們將", "希望這篇文章對你有所幫助",
    # English
    "in today's fast-paced world", "in today's digital age", "in the ever-evolving",
    "delve into", "it's important to note", "it is important to note", "unlock the power",
    "game-changer", "navigating the complexities", "in conclusion,", "a testament to",
    "embark on a journey", "look no further",
)

_SHORTCODE = re.compile(r"\[\[[a-z]+:[^\]]*\]\]")
_EMPTY_ALT_MD = re.compile(r"!\[\s*\]\(")
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_NON_PARAGRAPH = re.compile(r"^(#|\||[-*+]\s|>|<|\[\[|!\[|\d+[.)]\s|```|~~~)")


@dataclass(frozen=True)
class QualityConfig:
    min_words: int = 800
    title_width: tuple[int, int] = (20, 60)
    description_width: tuple[int, int] = (70, 160)
    min_h2: int = 2
    max_paragraph_words: int = 80
    banned_phrases: tuple[str, ...] = AI_FILLER_PHRASES

    @classmethod
    def from_mapping(cls, data: Mapping | None) -> "QualityConfig":
        data = dict(data or {})
        kwargs = {}
        for key in ("min_words", "min_h2", "max_paragraph_words"):
            if key in data:
                kwargs[key] = int(data[key])
        for key in ("title_width", "description_width"):
            if key in data:
                lo, hi = data[key]
                kwargs[key] = (int(lo), int(hi))
        if data.get("extra_banned_phrases"):
            kwargs["banned_phrases"] = AI_FILLER_PHRASES + tuple(data["extra_banned_phrases"])
        return cls(**kwargs)


@dataclass(frozen=True)
class Issue:
    rule: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class QualityReport:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def score(self) -> int:
        return max(0, 100 - 15 * len(self.errors) - 5 * len(self.warnings))

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": [i.__dict__ for i in self.issues],
        }


def _keyword_parts(keyword: str) -> list[str]:
    return [p.lower() for p in keyword.split() if p]


def _contains_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    return all(part in lowered for part in _keyword_parts(keyword))


def _blocks(md_text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", md_text) if b.strip()]


def check_article(article: Article, offers: Mapping | None = None, config: QualityConfig | None = None) -> QualityReport:
    cfg = config or QualityConfig()
    report = QualityReport()
    add = lambda rule, sev, msg: report.issues.append(Issue(rule, sev, msg))  # noqa: E731

    body = _SHORTCODE.sub("", article.body_md)
    body_lower = body.lower()

    # --- 標題 ---
    if not _contains_keyword(article.title, article.keyword):
        add("keyword-in-title", "error", f"標題沒有包含目標關鍵字「{article.keyword}」")
    width = display_width(article.title)
    lo, hi = cfg.title_width
    if not lo <= width <= hi:
        add("title-length", "warning", f"標題寬度 {width}，建議 {lo}–{hi}（中文字算 2）以免在搜尋結果被截斷")

    # --- Meta description ---
    if not article.description:
        add("meta-description", "error", "缺少 description，Google 會自行抓取內文、點閱率通常較差")
    else:
        dw = display_width(article.description)
        lo, hi = cfg.description_width
        if not lo <= dw <= hi:
            add("meta-description", "warning", f"description 寬度 {dw}，建議 {lo}–{hi}")

    # --- 結構 ---
    lines = body.splitlines()
    if any(re.match(r"^#\s", line) for line in lines):
        add("single-h1", "error", "內文不可再有 H1（# ），標題已是頁面唯一的 H1")
    h2_count = sum(1 for line in lines if re.match(r"^##\s", line))
    if h2_count < cfg.min_h2:
        add("h2-structure", "warning", f"只有 {h2_count} 個 H2，建議至少 {cfg.min_h2} 個以利精選摘要與廣告版位")

    blocks = _blocks(body)
    paragraphs = [b for b in blocks if not _NON_PARAGRAPH.match(b)]
    if paragraphs and not _contains_keyword(paragraphs[0], article.keyword):
        add("keyword-in-intro", "warning", "第一段沒有出現目標關鍵字")
    for para in paragraphs:
        n = word_count(para)
        if n > cfg.max_paragraph_words:
            add("long-paragraph", "warning", f"段落 {n} 字過長（上限 {cfg.max_paragraph_words}），手機閱讀會勸退：{para[:20]}…")

    # --- 內容量與套話 ---
    words = word_count(strip_html(render_markdown(body)))
    if words < cfg.min_words:
        add("thin-content", "error", f"內容只有 {words} 字，低於門檻 {cfg.min_words}")
    for phrase in cfg.banned_phrases:
        if phrase.lower() in body_lower or phrase.lower() in article.title.lower():
            add("ai-filler", "error", f"偵測到 AI 套話「{phrase}」，請改寫成具體經驗或數據")

    # --- 圖片 ---
    for _ in _EMPTY_ALT_MD.finditer(body):
        add("image-alt", "error", "圖片缺少替代文字（alt）")
    for tag in _IMG_TAG.findall(body):
        if not re.search(r'\balt\s*=\s*"[^"]+"', tag, re.I):
            add("image-alt", "error", f"HTML 圖片缺少 alt：{tag[:40]}")

    return report
