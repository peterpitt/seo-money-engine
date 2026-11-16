"""關鍵字金礦評估：搜尋意圖判斷、錢景分數、主題分群。

CPC 一律以 USD 計，讓台灣與美國市場的關鍵字可以放在同一張表比較。
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping

from .text import tokens

SUPPORTED_MARKETS = ("tw", "us")


class Intent(str, Enum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"


# 依序判斷：導航 > 交易 > 商業調查 > 資訊
_MARKERS: list[tuple[Intent, list[str], list[str]]] = [
    (
        Intent.NAVIGATIONAL,
        ["login", "log in", "sign in", "signin", "official site", "customer service", "app download"],
        ["登入", "官網", "客服電話", "會員中心"],
    ),
    (
        Intent.TRANSACTIONAL,
        ["buy", "coupon", "coupons", "discount", "promo code", "deal", "deals", "price", "pricing",
         "cheap", "cheapest", "for sale", "order", "free trial", "sign up"],
        ["優惠", "折扣", "折價", "購買", "哪裡買", "價格", "價錢", "團購", "便宜", "特價", "下單", "開戶", "申辦"],
    ),
    (
        Intent.COMMERCIAL,
        ["best", "top", "vs", "versus", "review", "reviews", "compare", "comparison", "alternative",
         "alternatives", "recommend", "recommended", "worth it", "rated"],
        ["推薦", "評價", "比較", "排名", "開箱", "評測", "心得", "ptt", "dcard", "值得買", "哪個好", "懶人包"],
    ),
]

INTENT_WEIGHT = {
    Intent.TRANSACTIONAL: 1.5,
    Intent.COMMERCIAL: 1.3,
    Intent.INFORMATIONAL: 1.0,
    Intent.NAVIGATIONAL: 0.2,
}


def _has_latin_marker(text: str, marker: str) -> bool:
    pattern = r"(?<![a-z0-9])" + r"\s+".join(map(re.escape, marker.split())) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def classify_intent(term: str) -> Intent:
    text = term.lower()
    for intent, latin, cjk in _MARKERS:
        if any(_has_latin_marker(text, m) for m in latin) or any(m in text for m in cjk):
            return intent
    return Intent.INFORMATIONAL


_ALIASES = {
    "term": ("keyword", "term", "query", "關鍵字"),
    "volume": ("volume", "search volume", "monthly volume", "搜尋量"),
    "cpc": ("cpc", "cpc (usd)", "單次點擊出價"),
    "difficulty": ("difficulty", "kd", "keyword difficulty", "難度"),
    "market": ("market", "市場"),
    "intent": ("intent", "意圖"),
}


def _number(raw: str) -> float:
    cleaned = re.sub(r"[^\d.\-]", "", str(raw))
    if cleaned in ("", "-", "."):
        raise ValueError(f"not a number: {raw!r}")
    return float(cleaned)


@dataclass
class Keyword:
    term: str
    volume: int
    cpc: float
    difficulty: int
    market: str = "tw"
    intent: Intent | None = None

    def __post_init__(self) -> None:
        self.term = " ".join(self.term.split())
        if not self.term:
            raise ValueError("keyword term is empty")
        if self.volume < 0:
            raise ValueError("volume must be >= 0")
        if self.cpc < 0:
            raise ValueError("cpc must be >= 0")
        if not 0 <= self.difficulty <= 100:
            raise ValueError("difficulty must be within 0..100")
        self.market = self.market.lower()
        if self.market not in SUPPORTED_MARKETS:
            raise ValueError(f"market must be one of {SUPPORTED_MARKETS}, got {self.market!r}")
        if self.intent is None:
            self.intent = classify_intent(self.term)
        elif not isinstance(self.intent, Intent):
            self.intent = Intent(str(self.intent).lower())

    @classmethod
    def from_mapping(cls, row: Mapping[str, str]) -> "Keyword":
        normalized = {str(k).strip().lower(): v for k, v in row.items() if k is not None}

        def pick(field: str, default=None):
            for alias in _ALIASES[field]:
                value = normalized.get(alias)
                if value not in (None, ""):
                    return value
            if default is None:
                raise ValueError(f"missing column: {field}")
            return default

        return cls(
            term=str(pick("term")).strip(),
            volume=int(_number(pick("volume"))),
            cpc=_number(pick("cpc")),
            difficulty=int(_number(pick("difficulty"))),
            market=str(pick("market", "tw")).strip(),
            intent=(str(pick("intent", "")).strip() or None),
        )


def opportunity_score(kw: Keyword) -> float:
    """錢景分數 = 搜尋量 × CPC × 意圖權重 × (可排名機率)²，難度越高衰減越快。"""
    rankability = (100 - kw.difficulty) / 100
    return round(kw.volume * kw.cpc * INTENT_WEIGHT[kw.intent] * rankability**2, 4)


def prioritize(
    keywords: Iterable[Keyword],
    *,
    max_difficulty: int | None = None,
    min_volume: int = 0,
    top: int | None = None,
) -> list[Keyword]:
    selected = [
        k for k in keywords
        if k.volume >= min_volume and (max_difficulty is None or k.difficulty <= max_difficulty)
    ]
    selected.sort(key=lambda k: (-opportunity_score(k), -k.volume, k.term))
    return selected[:top] if top else selected


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def cluster_keywords(keywords: Iterable[Keyword], threshold: float = 0.5) -> list[list[Keyword]]:
    """貪婪分群：分數最高的關鍵字當支柱頁（pillar），相似者歸為同一群。"""
    clusters: list[tuple[set[str], list[Keyword]]] = []
    for kw in prioritize(keywords):
        feats = tokens(kw.term)
        for seed, members in clusters:
            if members[0].market == kw.market and _jaccard(seed, feats) >= threshold:
                members.append(kw)
                break
        else:
            clusters.append((feats, [kw]))
    return [members for _, members in clusters]


# ---------------------------------------------------------------- 讀檔：各種實際格式
# Google Ads 匯出是 UTF-16 + Tab；台灣 Windows 的 Excel 另存 CSV 是 Big5（cp950）

def _decode(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp950")


_TERM_HEADERS = {"keyword", "term", "query", "關鍵字", "关键字"}


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    lines = _decode(Path(path).read_bytes()).splitlines()
    for i, line in enumerate(lines[:10]):   # 規劃工具的匯出檔前面有標題列
        delim = "\t" if line.count("\t") > line.count(",") else ","
        header = [c.strip().lower() for c in next(csv.reader([line], delimiter=delim))]
        if _TERM_HEADERS & set(header):
            reader = csv.DictReader(lines[i:], delimiter=delim)
            return [row for row in reader if any((v or "").strip() for v in row.values())]
    first = lines[0] if lines else ""
    raise ValueError(f"找不到關鍵字欄位（keyword／關鍵字）。檔案第一行是：{first[:80]!r}")


_UNIT = {"k": 1_000, "m": 1_000_000, "万": 10_000, "萬": 10_000}


def _one_volume(token: str) -> float:
    m = re.fullmatch(r"([\d.]+)\s*([kKmM万萬]?)", token.replace(",", "").strip())
    if not m:
        raise ValueError(f"not a volume: {token!r}")
    return float(m.group(1)) * _UNIT.get(m.group(2).lower() if m.group(2) else "", 1)


def parse_volume(raw: str) -> int | None:
    """把「1,900」「100 – 1K」「1万 – 10万」轉成一個數字；範圍取幾何中間值。沒有資料回傳 None。"""
    text = str(raw or "").strip()
    if text in ("", "-", "--", "—", "–"):
        return None
    parts = [p for p in re.split(r"\s*[–—-]\s*", text) if p]
    nums = [_one_volume(p) for p in parts]
    if len(nums) == 1:
        return round(nums[0])
    return round(math.sqrt(nums[0] * nums[1]))


def _find(header: Iterable[str], *needles: str) -> str | None:
    for col in header:
        name = col.strip().lower()
        if any(n in name for n in needles):
            return col
    return None


_COMPETITION_LABEL = {"low": 20, "低": 20, "medium": 50, "中": 50, "high": 85, "高": 85}
_CJK = re.compile(r"[぀-ヿ㐀-鿿]")


def _planner_rows(rows: list[dict[str, str]], fx_to_usd: Mapping[str, float], market: str | None) -> list[Keyword]:
    header = list(rows[0].keys()) if rows else []
    c_term = _find(header, "keyword", "關鍵字", "关键字")
    c_vol = _find(header, "monthly searches", "每月搜索量", "每月搜尋量")
    c_low = _find(header, "low range", "低位", "低標", "低价", "低價")
    c_high = _find(header, "high range", "高位", "高標", "高价", "高價")
    c_idx = _find(header, "indexed", "索引", "指數", "指数")
    c_comp = _find(header, "competition", "竞争", "競爭")
    c_cur = _find(header, "currency", "货币", "貨幣", "幣別")
    out = []
    for row in rows:
        term = (row.get(c_term) or "").strip()
        volume = parse_volume(row.get(c_vol, ""))
        if not term or not volume:
            continue
        bids = [float(re.sub(r"[^\d.]", "", v)) for v in (row.get(c_low), row.get(c_high))
                if v and re.sub(r"[^\d.]", "", v)]
        mid = sum(bids) / len(bids) if bids else 0.0
        currency = (row.get(c_cur) or "USD").strip().upper() or "USD"
        rate = 1.0 if currency == "USD" else fx_to_usd.get(currency)
        if mid and rate is None:
            raise ValueError(f"出價幣別是 {currency}，請在 site.yaml 的 google.fx_to_usd 設定 {currency} 對美元匯率"
                             f"（或用 --fx {currency}=0.03 指定）")
        idx = (row.get(c_idx) or "").strip() if c_idx else ""
        label = (row.get(c_comp) or "").strip().lower() if c_comp and c_comp != c_idx else ""
        difficulty = int(float(idx)) if idx else _COMPETITION_LABEL.get(label, 50)
        out.append(Keyword(term=term, volume=volume, cpc=round(mid * (rate or 1.0), 4),
                           difficulty=max(0, min(100, difficulty)),
                           market=market or ("tw" if _CJK.search(term) else "us")))
    return out


def site_fx(project_dir: str | Path) -> dict[str, float]:
    """site.yaml 的 google.fx_to_usd（Google Ads 帳戶非美元時的匯率）。"""
    import yaml

    path = Path(project_dir) / "site.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k).upper(): float(v) for k, v in ((data.get("google") or {}).get("fx_to_usd") or {}).items()}


def load_keywords_csv(path: str | Path, fx_to_usd: Mapping[str, float] | None = None,
                      market: str | None = None) -> list[Keyword]:
    """讀自家格式或 Google Ads 關鍵字規劃工具的匯出檔（任何常見編碼、逗號或 Tab）。"""
    rows = _read_rows(path)
    header = {k.strip().lower() for k in (rows[0].keys() if rows else []) if k}
    if header & set(_ALIASES["volume"]) or not rows:
        return [Keyword.from_mapping(row) for row in rows]
    return _planner_rows(rows, fx_to_usd or {}, market)
