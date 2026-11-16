import datetime as dt
import importlib.util
import json
import os

import pytest
import yaml

from google_fakes import FakeAdsBackend, explore_csv, rss_xml
from helpers import article_md, write_project
from seoengine import cli
from seoengine.google import ads as ads_mod
from seoengine.google.ads import AdsError, KeywordPlanner, ideas_to_rows, write_keywords_csv
from seoengine.google.auth import create_ads_yaml
from seoengine.google.opportunities import rank_opportunities
from seoengine.google.trends import (
    TrendingItem,
    fetch_trending,
    filter_trending,
    parse_explore_csv,
    parse_traffic,
    parse_trending_rss,
    seasonality,
)

D = dt.date


# ---------------------------------------------------------------- Trends RSS
@pytest.mark.parametrize("raw, n", [("200K+", 200_000), ("1M+", 1_000_000), ("2,000+", 2000), ("500+", 500), ("", 0)])
def test_parse_traffic(raw, n):
    assert parse_traffic(raw) == n


def test_parse_rss_fields():
    [item] = parse_trending_rss(rss_xml([{"title": "eid al fitr 2027", "traffic": "50K+"}]), geo="AE")
    assert (item.title, item.traffic, item.geo) == ("eid al fitr 2027", 50_000, "AE")
    assert item.published.isoformat() == "2026-10-22T23:30:00-07:00"
    assert item.news[0] == {"title": "Story about eid al fitr 2027", "url": "https://news.example.com/a", "source": "Example News"}


def test_parse_rss_rejects_garbage():
    with pytest.raises(ValueError):
        parse_trending_rss("<html>blocked</html>", geo="US")


def test_filter_is_case_insensitive_and_excludes():
    items = [TrendingItem("Golden Week Japan", 1000, "1K+", None, "JP"), TrendingItem("holiday inn stock", 900, "", None, "US")]
    out = filter_trending(items, include=["golden week", "holiday"], exclude=["stock"])
    assert [i.title for i in out] == ["Golden Week Japan"]


def test_fetch_trending_uses_official_rss_url():
    seen = {}

    def fake_get(url, timeout):
        seen["url"] = url
        return rss_xml([{"title": "a holiday", "traffic": "1K+"}])

    items = fetch_trending("jp", http_get=fake_get)
    assert seen["url"] == "https://trends.google.com/trending/rss?geo=JP"
    assert items[0].geo == "JP"


# ---------------------------------------------------------------- Explore CSV
def test_parse_explore_csv_handles_header_and_less_than_one():
    [s] = parse_explore_csv(explore_csv("public holidays", peak_month=1))
    assert s.keyword == "public holidays" and s.geo == "United States"
    assert all(v >= 0 for _, v in s.points) and 0.5 in [v for _, v in s.points]


def test_parse_explore_csv_multiple_columns():
    text = "Week,a: (Japan),b: (Japan)\n2026-01-04,10,20\n2026-01-11,30,<1\n"
    series = parse_explore_csv(text)
    assert [s.keyword for s in series] == ["a", "b"]
    assert series[1].points[1][1] == 0.5


def test_parse_explore_csv_without_data_raises():
    with pytest.raises(ValueError):
        parse_explore_csv("Category: All categories\n\n")


def test_seasonality_publish_by_rolls_to_next_year():
    [s] = parse_explore_csv(explore_csv("x", peak_month=3))
    season = seasonality(s, today=D(2026, 10, 24))
    assert season.peak_month == 3 and season.publish_by == D(2027, 1, 18)
    assert season.monthly_avg[3] > season.monthly_avg[7]


# ---------------------------------------------------------------- Ads
def _planner(currency="USD", ideas=None):
    ideas = ideas or [{"text": "Public Holidays 2027 ", "avg_monthly_searches": "100", "competition_index": "80",
                       "low_bid_micros": "1000000", "high_bid_micros": "3000000"}]
    return KeywordPlanner(FakeAdsBackend(currency, ideas), customer_id="123-456-7890")


def test_planner_normalizes_customer_id_and_resolves_constants():
    p = _planner()
    list(p.ideas(["public holidays"], country="us", language="zh-TW"))
    req = p.backend.requests[0]
    assert req["customer_id"] == "1234567890"
    assert req["geos"] == ["geoTargetConstants/2840"]
    assert any("country_code = 'US'" in q for q in p.backend.queries)
    assert any("language_constant.code = 'zh_TW'" in q for q in p.backend.queries)


def test_planner_requires_seed_or_url():
    with pytest.raises(AdsError):
        list(_planner().ideas([], country="US", language="en"))


def test_planner_rejects_bad_input_injection():
    with pytest.raises(AdsError):
        list(_planner().ideas(["x"], country="US' OR 1=1", language="en"))


def test_ideas_to_rows_usd_and_market():
    p = _planner()
    [row] = ideas_to_rows(p.ideas(["x"], country="US", language="en"), market="us", currency="USD", fx_to_usd={})
    assert row["keyword"] == "public holidays 2027"          # 去空白、轉小寫
    assert (row["volume"], row["difficulty"], row["cpc"]) == (100, 80, 2.0)
    assert row["source"] == "google-ads" and row["currency"] == "USD"


def test_ideas_to_rows_skips_zero_volume_and_dedupes():
    ideas = [{"text": "a", "avg_monthly_searches": "0", "competition_index": "1", "low_bid_micros": "0", "high_bid_micros": "0"},
             {"text": "b", "avg_monthly_searches": "10", "competition_index": "1", "low_bid_micros": "0", "high_bid_micros": "0"},
             {"text": "B", "avg_monthly_searches": "10", "competition_index": "1", "low_bid_micros": "0", "high_bid_micros": "0"}]
    p = _planner(ideas=ideas)
    rows = ideas_to_rows(p.ideas(["x"], country="US", language="en"), market="us", currency="USD", fx_to_usd={})
    assert [r["keyword"] for r in rows] == ["b"]


def test_write_keywords_csv_merges_with_existing(tmp_path):
    path = tmp_path / "k.csv"
    write_keywords_csv([{"keyword": "a", "volume": 1, "cpc": 0.1, "difficulty": 1, "market": "us", "source": "google-ads"}], path)
    write_keywords_csv([{"keyword": "a", "volume": 9, "cpc": 0.2, "difficulty": 2, "market": "us", "source": "google-ads"},
                        {"keyword": "b", "volume": 5, "cpc": 0.3, "difficulty": 3, "market": "us", "source": "google-ads"}], path, merge=True)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("keyword,volume,cpc,difficulty,market,source")
    assert len(lines) == 3 and lines[1].startswith("a,9,")


def test_load_backend_without_config_explains_setup(tmp_path):
    with pytest.raises(AdsError, match="seoengine ads auth"):
        ads_mod.load_backend(tmp_path / "missing.yaml")


@pytest.mark.skipif(importlib.util.find_spec("google.ads") is None, reason="google-ads 未安裝")
def test_real_request_builder_sets_v26_fields_offline():
    from google.ads.googleads.client import GoogleAdsClient
    from google.oauth2.credentials import Credentials

    client = GoogleAdsClient(Credentials(token="offline"), developer_token="x", use_proto_plus=True)
    backend = ads_mod.GoogleAdsBackend(client)
    req = backend.build_request("1234567890", ["public holidays"], None, ["geoTargetConstants/2840"], "languageConstants/1000")
    assert req.customer_id == "1234567890" and list(req.keyword_seed.keywords) == ["public holidays"]
    assert list(req.geo_target_constants) == ["geoTargetConstants/2840"] and req.language == "languageConstants/1000"
    assert req.include_adult_keywords is False
    req2 = backend.build_request("1", ["a"], "https://h.example.com/", [], "languageConstants/1000")
    assert req2.keyword_and_url_seed.url == "https://h.example.com/"


# ---------------------------------------------------------------- OAuth
class FakeFlow:
    def __init__(self):
        # 與 google_auth_oauthlib 實際行為相同：client_config 是 "installed" 內層的內容
        self.client_config = {"client_id": "cid.apps.googleusercontent.com", "client_secret": "sec"}
        self.scopes = None

    def run_local_server(self, port=0, **kw):
        return type("Cred", (), {"refresh_token": "1//refresh"})()


def test_create_ads_yaml_writes_private_file(tmp_path):
    out = tmp_path / "secrets" / "google-ads.yaml"
    flows = []

    def factory(path, scopes):
        f = FakeFlow(); f.scopes = scopes; flows.append(f); return f

    create_ads_yaml(tmp_path / "client_secret.json", "DEVTOKEN", "123-456-7890", out,
                    login_customer_id="111-222-3333", flow_factory=factory)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data == {"developer_token": "DEVTOKEN", "client_id": "cid.apps.googleusercontent.com", "client_secret": "sec",
                    "refresh_token": "1//refresh", "use_proto_plus": True, "customer_id": "1234567890",
                    "login_customer_id": "1112223333"}
    assert flows[0].scopes == ["https://www.googleapis.com/auth/adwords"]
    if os.name != "nt":  # Windows 沒有 POSIX 權限位元
        assert (out.stat().st_mode & 0o077) == 0
    assert (tmp_path / "secrets" / ".gitignore").read_text() == "*\n"


# ---------------------------------------------------------------- 流量機會
@pytest.fixture
def project(tmp_path):
    root = write_project(tmp_path / "p")
    (root / "keywords.csv").write_text(
        "keyword,volume,cpc,difficulty,market,source\n"
        "japan public holidays 2027,4500,0.5,22,us,google-ads\n"
        "日本連假 2027,3500,0.25,8,tw,google-ads\n", encoding="utf-8")
    return root


def test_rank_without_trending_or_seasonality(project):
    opps = rank_opportunities(project)
    assert {o.term for o in opps} == {"japan public holidays 2027", "日本連假 2027"}
    assert all(o.forecast_total > 0 and o.currency in ("USD", "TWD") for o in opps)


def test_seasonality_urgency_boosts_score(project):
    (project / "data").mkdir()
    (project / "data" / "seasonality.json").write_text(json.dumps(
        {"japan public holidays": {"peak_month": 1, "publish_by": "2026-11-20"}}), encoding="utf-8")
    opps = {o.term: o for o in rank_opportunities(project, today=D(2026, 10, 24))}
    jp = opps["japan public holidays 2027"]
    assert jp.peak_month == 1 and jp.publish_by == "2026-11-20" and jp.urgent


def test_rank_writes_json_report(project):
    rank_opportunities(project)
    data = json.loads((project / "data" / "opportunities.json").read_text(encoding="utf-8"))
    assert data[0]["term"] and "score" in data[0]


def test_brief_skips_existing_files(project):
    (project / "content" / "japan-public-holidays-2027.md").write_text(article_md("x", "something", lang="en"), encoding="utf-8")
    opps = rank_opportunities(project, brief_top=2)
    assert all(o.brief_path is None or "日本" in o.term or o.brief_path.endswith(".md") for o in opps)


def test_requires_keywords_file(tmp_path):
    root = write_project(tmp_path / "empty")
    with pytest.raises(FileNotFoundError, match="seoengine ads ideas"):
        rank_opportunities(root)


# ---------------------------------------------------------------- CLI
def test_cli_trends_import(tmp_path, project, capsys):
    csv = tmp_path / "multiTimeline.csv"
    csv.write_text(explore_csv("japan public holidays", peak_month=1), encoding="utf-8")
    assert cli.main(["trends", "import", str(csv), "--project", str(project)]) == 0
    data = json.loads((project / "data" / "seasonality.json").read_text(encoding="utf-8"))
    assert data["japan public holidays"]["peak_month"] == 1
    assert "1 月" in capsys.readouterr().out


def test_cli_trends_trending_offline(monkeypatch, project, capsys):
    monkeypatch.setattr("seoengine.google.trends._http_get",
                        lambda url, timeout: rss_xml([{"title": "golden week 2027", "traffic": "5K+"},
                                                      {"title": "nba scores", "traffic": "200K+"}]))
    assert cli.main(["trends", "trending", "--geo", "JP", "--include", "golden week", "--project", str(project)]) == 0
    saved = json.loads((project / "data" / "trending.json").read_text(encoding="utf-8"))
    assert [i["title"] for i in saved] == ["golden week 2027"]
    assert "golden week 2027" in capsys.readouterr().out


def test_cli_ads_ideas_with_fake_backend(monkeypatch, project, capsys):
    fake = FakeAdsBackend("USD", [{"text": "italy public holidays 2027", "avg_monthly_searches": "2400",
                                   "competition_index": "15", "low_bid_micros": "300000", "high_bid_micros": "500000"}])
    monkeypatch.setattr(ads_mod, "load_backend", lambda path: (fake, "1234567890"))
    code = cli.main(["ads", "ideas", "--project", str(project), "--seed", "italy public holidays", "--geo", "IT", "--lang", "en"])
    assert code == 0
    text = (project / "keywords.csv").read_text(encoding="utf-8")
    assert "italy public holidays 2027,2400,0.4,15,us,google-ads" in text
    assert "日本連假 2027" in text                       # 既有資料保留


def test_cli_opportunities(project, capsys):
    assert cli.main(["opportunities", "--project", str(project), "--brief", "1"]) == 0
    out = capsys.readouterr().out
    assert "japan public holidays 2027" in out and "草稿" in out


def test_create_ads_yaml_without_developer_token(tmp_path):
    """2026-09-09 起 developer token 已停用（API 會忽略），權限改由 Cloud 專案控管，所以不再必填。"""
    out = tmp_path / "google-ads.yaml"
    create_ads_yaml(tmp_path / "cs.json", "", "1234567890", out, flow_factory=lambda p, s: FakeFlow())
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert "developer_token" not in data and data["refresh_token"] == "1//refresh"


def test_cli_ads_auth_developer_token_optional():
    parser = cli.build_parser()
    args = parser.parse_args(["ads", "auth", "--client-secrets", "cs.json", "--customer-id", "123-456-7890"])
    assert args.developer_token is None
