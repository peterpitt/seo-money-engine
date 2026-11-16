"""文字工具：中英混排的 slug、字數、顯示寬度與分詞。"""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata

CJK_RANGES = r"㐀-䶿一-鿿豈-﫿぀-ヿ가-힯"
_CJK_CHAR = re.compile(f"[{CJK_RANGES}]")
_CJK_RUN = re.compile(f"[{CJK_RANGES}]+")
_LATIN_WORD = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
_TAG = re.compile(r"<[^>]+>")

STOPWORDS = frozenset(
    """a an the and or but of to in on for with at by from as is are was were be been
    how what why when where which who whom this that these those it its your you my our
    do does did can should would i me we they them their there here vs""".split()
)


def slugify(text: str) -> str:
    """產生 URL slug。純中文無法轉寫時，用穩定雜湊避免中文網址被編碼成一長串。"""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if slug:
        return slug
    return "p-" + hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:8]


def display_width(text: str) -> int:
    """以「半形字元」為單位的寬度，全形 / 中日韓字 = 2。用來估算 SERP 標題截斷。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def word_count(text: str) -> int:
    """中日韓每個字算 1，英文以單字計。"""
    return len(_CJK_CHAR.findall(text)) + len(_LATIN_WORD.findall(text))


def strip_html(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", markup))).strip()


def tokens(text: str) -> set[str]:
    """分群用的特徵：英文單字（去停用詞）＋ 中文雙字詞。"""
    out: set[str] = set()
    for word in _LATIN_WORD.findall(text.lower()):
        if word not in STOPWORDS:
            out.add(word)
    for run in _CJK_RUN.findall(text):
        if len(run) == 1:
            out.add(run)
        else:
            out.update(run[i : i + 2] for i in range(len(run) - 1))
    return out


def is_latin(text: str) -> bool:
    return not _CJK_CHAR.search(text)
