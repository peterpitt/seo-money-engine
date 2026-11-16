"""Google Ads API Keyword Planner：取得真實的月搜尋量、競爭度與首頁出價。

需要：Google Ads 帳戶、Google Cloud 專案（已啟用 Google Ads API，存取等級至少 Basic——
Explorer 等級會封鎖 Keyword Planner）、OAuth 用戶端（桌面應用程式）。
developer token 已於 2026-09-09 停用，權限改由 Cloud 專案控管。
設定檔用 `seoengine ads auth` 產生（secrets/google-ads.yaml，不會進版本控制）。
國家與語言常數在執行時用 GAQL 查詢，不寫死 ID。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, Mapping

COLUMNS = ["keyword", "volume", "cpc", "difficulty", "market", "source", "competition_index",
           "cpc_low", "cpc_high", "currency", "geo", "language"]


class AdsError(RuntimeError):
    pass


def _customer_id(raw: str) -> str:
    cid = re.sub(r"\D", "", str(raw or ""))
    if len(cid) != 10:
        raise AdsError(f"Google Ads 客戶 ID 應為 10 碼數字（例如 123-456-7890），收到 {raw!r}")
    return cid


class GoogleAdsBackend:
    """真正呼叫 Google Ads API 的薄層（google-ads 官方函式庫）。"""

    def __init__(self, client):
        self.client = client

    def search(self, customer_id: str, query: str):
        service = self.client.get_service("GoogleAdsService")
        return list(service.search(customer_id=customer_id, query=query))

    def build_request(self, customer_id: str, seeds: list[str], url: str | None,
                      geo_resource_names: list[str], language_resource_name: str):
        req = self.client.get_type("GenerateKeywordIdeasRequest")
        req.customer_id = customer_id
        req.language = language_resource_name
        req.geo_target_constants.extend(geo_resource_names)
        req.include_adult_keywords = False
        req.keyword_plan_network = self.client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        if seeds and url:
            req.keyword_and_url_seed.url = url
            req.keyword_and_url_seed.keywords.extend(seeds)
        elif url:
            req.url_seed.url = url
        else:
            req.keyword_seed.keywords.extend(seeds)
        return req

    def generate_keyword_ideas(self, customer_id, seeds, url, geo_resource_names, language_resource_name, limit):
        req = self.build_request(customer_id, seeds, url, geo_resource_names, language_resource_name)
        service = self.client.get_service("KeywordPlanIdeaService")
        for i, idea in enumerate(service.generate_keyword_ideas(request=req)):
            if i >= limit:
                break
            yield idea


def load_backend(config_path: str | Path):
    """讀取 google-ads.yaml，回傳（後端, 客戶 ID）。"""
    path = Path(config_path)
    if not path.exists():
        raise AdsError(
            f"找不到 {path}。請先執行 `seoengine ads auth --client-secrets <client_secret.json> "
            "--customer-id <123-456-7890>` 建立設定檔（步驟見 docs/google-setup.md）。")
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:  # pragma: no cover - 依安裝環境而定
        raise AdsError('尚未安裝 Google Ads 函式庫，請執行：pip install -e ".[google]"') from exc
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    customer = _customer_id(data.pop("customer_id", ""))
    client = GoogleAdsClient.load_from_dict({k: v for k, v in data.items() if v not in (None, "")})
    return GoogleAdsBackend(client), customer


class KeywordPlanner:
    def __init__(self, backend, customer_id: str):
        self.backend = backend
        self.customer_id = _customer_id(customer_id)
        self._currency: str | None = None

    def account_currency(self) -> str:
        if self._currency is None:
            rows = self.backend.search(self.customer_id, "SELECT customer.currency_code FROM customer LIMIT 1")
            if not rows:
                raise AdsError("查不到帳戶幣別")
            self._currency = rows[0].customer.currency_code
        return self._currency

    def geo_resource(self, country: str) -> str:
        code = country.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", code):
            raise AdsError(f"國家代碼應為兩個英文字母（例如 US、JP），收到 {country!r}")
        rows = self.backend.search(self.customer_id, (
            "SELECT geo_target_constant.resource_name FROM geo_target_constant "
            f"WHERE geo_target_constant.country_code = '{code}' "
            "AND geo_target_constant.target_type = 'Country' AND geo_target_constant.status = 'ENABLED'"))
        if not rows:
            raise AdsError(f"Google Ads 找不到國家 {code}")
        return rows[0].geo_target_constant.resource_name

    def language_resource(self, language: str) -> str:
        code = language.strip().replace("-", "_")
        if not re.fullmatch(r"[a-z]{2,3}(_[A-Z]{2})?", code):
            raise AdsError(f"語言代碼格式錯誤（例如 en、ja、zh_TW），收到 {language!r}")
        rows = self.backend.search(self.customer_id, (
            "SELECT language_constant.resource_name FROM language_constant "
            f"WHERE language_constant.code = '{code}'"))
        if not rows:
            raise AdsError(f"Google Ads 找不到語言 {code}")
        return rows[0].language_constant.resource_name

    def ideas(self, seeds: list[str], country: str, language: str, url: str | None = None, limit: int = 200):
        seeds = [s.strip() for s in seeds if s and s.strip()][:20]
        if not seeds and not url:
            raise AdsError("至少要提供一個種子關鍵字或網址")
        geo = self.geo_resource(country)
        lang = self.language_resource(language)
        return self.backend.generate_keyword_ideas(self.customer_id, seeds, url, [geo], lang, limit)


def ideas_to_rows(ideas: Iterable, market: str, currency: str, fx_to_usd: Mapping[str, float],
                  geo: str = "", language: str = "") -> list[dict]:
    """轉成 keywords.csv 的列。CPC 取首頁出價高低的中間值並換算成美元；難度用廣告競爭指數（0–100）作為代理指標。"""
    currency = (currency or "USD").upper()
    rate = 1.0 if currency == "USD" else fx_to_usd.get(currency)
    if rate is None:
        raise AdsError(f"Google Ads 帳戶幣別是 {currency}，請在 site.yaml 的 google.fx_to_usd 設定 {currency} 對美元匯率")
    rows, seen = [], set()
    for idea in ideas:
        term = " ".join(str(idea.text).split()).lower()
        m = idea.keyword_idea_metrics
        volume = int(m.avg_monthly_searches or 0)
        if not term or volume <= 0 or term in seen:
            continue
        seen.add(term)
        low, high = (m.low_top_of_page_bid_micros or 0) / 1e6, (m.high_top_of_page_bid_micros or 0) / 1e6
        mid = (low + high) / 2 if (low or high) else (getattr(m, "average_cpc_micros", 0) or 0) / 1e6
        rows.append({
            "keyword": term, "volume": volume, "cpc": round(mid * rate, 4),
            "difficulty": max(0, min(100, int(m.competition_index or 0))), "market": market,
            "source": "google-ads", "competition_index": int(m.competition_index or 0),
            "cpc_low": round(low * rate, 4), "cpc_high": round(high * rate, 4), "currency": "USD",
            "geo": geo, "language": language,
        })
    return rows


def write_keywords_csv(rows: list[dict], path: str | Path, merge: bool = False) -> Path:
    """寫入 keywords.csv；merge=True 時保留既有關鍵字，同名的以新資料覆蓋。"""
    path = Path(path)
    existing: dict[str, dict] = {}
    if merge and path.exists():
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                key = (row.get("keyword") or "").strip().lower()
                if key:
                    existing[key] = row
    for row in rows:
        existing[row["keyword"]] = row
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in COLUMNS})
    return path
