import json

import pytest
import yaml

from helpers import article_md, write_project
from seoengine import cli
from seoengine.viz import (
    build_dashboard_data,
    extract_data,
    render_dashboard,
    write_dashboard,
)


@pytest.fixture
def project(tmp_path):
    root = write_project(tmp_path / "p")
    folder = root / "data" / "holidays"
    folder.mkdir(parents=True)
    jp = {"country": "Japan", "country_zh": "日本", "code": "jp",
          "holidays": [{"date": "2027-04-29", "name": "Showa Day", "local": "昭和の日"},
                       {"date": "2027-05-03", "end": "2027-05-05", "name": "Golden Week"},
                       {"date": "2026-11-03", "name": "Culture Day"}]}
    us = {"country": "United States", "code": "us",
          "holidays": [{"date": "2027-07-05", "actual": "2027-07-04", "name": "Independence Day"}]}
    for code, data in (("jp", jp), ("us", us)):
        (folder / f"{code}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    (root / "offers.yaml").write_text("h1:\n  name: H1\n  url: https://a.brewlab.tw\n", encoding="utf-8")
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦", extra="[[cta:h1]]"), encoding="utf-8")
    (root / "content" / "bad.md").write_text(
        article_md("bad", "磨豆機保養", extra="在這個日新月異的時代。"), encoding="utf-8")
    return root


def test_dashboard_has_no_public_timeline(project):
    data = build_dashboard_data(project)
    assert "timeline" not in data
    assert 'id="timeline"' not in render_dashboard(data)


def test_pending_lists_estimated_holidays_with_country(project):
    folder = project / "data" / "holidays"
    (folder / "ae.yaml").write_text(
        "country: United Arab Emirates\ncountry_zh: 阿聯\ncode: ae\nholidays:\n"
        "  - {date: 2027-03-09, end: 2027-03-11, name: Eid Al Fitr holiday, name_zh: 開齋節假期, status: estimated}\n"
        "  - {date: 2027-12-02, name: National Day}\n", encoding="utf-8")
    pending = build_dashboard_data(project)["pending"]
    assert pending == [{"code": "ae", "country": "阿聯", "name": "開齋節假期", "start": "2027-03-09", "end": "2027-03-11"}]


def test_pipeline_counts(project):
    stages = {s["id"]: s for s in build_dashboard_data(project)["pipeline"]["stages"]}
    assert list(stages) == ["keywords", "articles", "gate", "monetize", "build", "measure"]
    assert stages["articles"]["value"] == 2
    assert (stages["gate"]["passed"], stages["gate"]["failed"]) == (1, 1)
    assert stages["monetize"]["value"] == 1          # 已發布文章用到的聯盟商品數
    assert stages["build"]["value"] == 1 + 3         # 1 篇文章 + 首頁 + 404 + 1 個跳轉頁
    assert stages["keywords"]["value"] == 0
    failed = [d for d in stages["gate"]["detail"] if not d["passed"]]
    assert failed[0]["slug"] == "bad" and "ai-filler" in failed[0]["rules"]


def test_revenue_none_without_keywords(project):
    assert build_dashboard_data(project)["revenue"] is None


def test_revenue_curve_has_twenty_positions_and_decreases(project, tmp_path):
    csv = tmp_path / "k.csv"
    csv.write_text("keyword,volume,cpc,difficulty,market\nbest grinder,1000,1.5,20,us\n", encoding="utf-8")
    rev = build_dashboard_data(project, keywords_path=csv)["revenue"]
    assert rev["example"] is False and rev["source"] == "k.csv"
    curve = rev["keywords"][0]["curve"]
    totals = [p["ad"] + p["aff"] for p in curve]
    assert [p["pos"] for p in curve] == list(range(1, 21))
    assert totals == sorted(totals, reverse=True)


def test_render_is_self_contained_and_roundtrips(project):
    data = build_dashboard_data(project)
    page = render_dashboard(data)
    assert page.lstrip().lower().startswith("<!doctype html>")
    assert "<script src" not in page
    assert extract_data(page) == json.loads(json.dumps(data))


def test_render_fragment_for_embedding(project):
    page = render_dashboard(build_dashboard_data(project), standalone=False)
    assert "<!doctype" not in page.lower() and "<title>" in page


def test_script_breakout_is_escaped(project):
    data = build_dashboard_data(project)
    data["site"]["name"] = "</script><script>alert(1)</script>"
    page = render_dashboard(data)
    assert "</script><script>alert(1)" not in page
    assert extract_data(page)["site"]["name"] == data["site"]["name"]


def test_owner_panels_present(project):
    page = render_dashboard(build_dashboard_data(project))
    for panel in ('id="pipeline"', 'id="revenue"', 'id="pending"'):
        assert panel in page
    assert "prefers-reduced-motion" in page


def test_write_dashboard_default_path(project):
    path = write_dashboard(project)
    assert path == project / "dashboard" / "index.html"


def test_cli_viz(project, tmp_path):
    out = tmp_path / "d.html"
    assert cli.main(["viz", str(project), "-o", str(out)]) == 0
    assert "viz-data" in out.read_text(encoding="utf-8")


def test_dashboard_includes_opportunities_and_trending(project):
    data_dir = project / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "opportunities.json").write_text(json.dumps([
        {"term": "uae public holidays 2027", "score": 3300, "forecast_total": 12.5, "currency": "USD",
         "trending": "public holidays in the uae", "urgent": True, "publish_by": "2026-11-20", "peak_month": 1,
         "covered_by": None, "brief_path": None, "market": "us", "volume": 6000, "cpc": 0.55, "difficulty": 18,
         "intent": "informational"}]), encoding="utf-8")
    (data_dir / "trending.json").write_text(json.dumps([{"title": "public holidays in the uae", "traffic": 20000,
                                                         "traffic_label": "20K+", "geo": "AE", "news": []}]), encoding="utf-8")
    data = build_dashboard_data(project)
    assert data["opportunities"][0]["term"] == "uae public holidays 2027"
    assert data["trending"][0]["geo"] == "AE"
    page = render_dashboard(data)
    assert 'id="opportunities"' in page


def test_revenue_source_marks_google_ads(project, tmp_path):
    csv = tmp_path / "keywords.csv"
    csv.write_text("keyword,volume,cpc,difficulty,market,source\na b,100,1,10,us,google-ads\n", encoding="utf-8")
    rev = build_dashboard_data(project, keywords_path=csv)["revenue"]
    assert rev["provider"] == "google-ads" and rev["example"] is False


def test_pending_shows_the_next_13_months_and_counts_the_rest(project):
    import datetime as dt
    folder = project / "data" / "holidays"
    (folder / "ae.yaml").write_text(
        "country: United Arab Emirates\ncountry_zh: 阿聯\ncode: ae\nholidays:\n"
        "  - {date: 2027-03-09, end: 2027-03-11, name: Eid Al Fitr holiday, name_zh: 開齋節假期, status: estimated}\n"
        "  - {date: 2029-02-14, end: 2029-02-16, name: Eid Al Fitr holiday, name_zh: 開齋節假期, status: estimated}\n",
        encoding="utf-8")
    data = build_dashboard_data(project, today=dt.date(2026, 10, 26))
    assert [p["start"] for p in data["pending"]] == ["2027-03-09"]
    assert data["pending_later"] == 1
    assert "pending_later" in render_dashboard(data)
