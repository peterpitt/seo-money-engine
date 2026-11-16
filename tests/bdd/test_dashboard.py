import json

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md, write_project
from seoengine.keywords import load_keywords_csv
from seoengine.revenue import forecast
from seoengine.viz import extract_data, write_dashboard

scenarios("../../features/dashboard.feature")


@given(parsers.parse('一個新的網站專案，網址為 "{url}"'))
def given_project(ctx, tmp_path, url):
    ctx["project"] = write_project(tmp_path / "site", base_url=url)


@given("專案有日本假日資料")
def given_jp(ctx):
    folder = ctx["project"] / "data" / "holidays"
    folder.mkdir(parents=True)
    data = {"country": "Japan", "country_zh": "日本", "code": "jp",
            "holidays": [{"date": "2027-05-03", "name": "Constitution Day"},
                         {"date": "2027-05-04", "name": "Greenery Day", "status": "estimated"}]}
    (folder / "jp.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"'))
def given_article(ctx, slug, keyword):
    (ctx["project"] / "content" / f"{slug}.md").write_text(article_md(slug, keyword), encoding="utf-8")


@given(parsers.parse('專案中有一篇草稿 "{slug}"'))
def given_draft(ctx, slug):
    (ctx["project"] / "content" / f"{slug}.md").write_text(article_md(slug, "磨豆機刻度", draft=True), encoding="utf-8")


@given(parsers.parse('關鍵字檔 "{name}" 內容為:'))
def given_keywords(ctx, name, datatable):
    path = ctx["project"] / name
    path.write_text("\n".join(",".join(row) for row in datatable) + "\n", encoding="utf-8")
    ctx["keywords_path"] = path


@when("我產生儀表板")
def when_dashboard(ctx):
    ctx["path"] = write_dashboard(ctx["project"], keywords_path=ctx["keywords_path"])
    ctx["html"] = ctx["path"].read_text(encoding="utf-8")
    ctx["data"] = extract_data(ctx["html"])


@then("儀表板檔案應存在")
def then_exists(ctx):
    assert ctx["path"].is_file() and ctx["html"].lstrip().lower().startswith("<!doctype html>")


@then("儀表板不應載入任何外部腳本")
def then_no_external(ctx):
    assert "<script src" not in ctx["html"]


@then("儀表板不應包含假日時間軸")
def then_no_timeline(ctx):
    assert "timeline" not in ctx["data"]
    assert 'id="timeline"' not in ctx["html"]


@then(parsers.parse('待官方公告的預估假日應有 {n:d} 筆，國家為 "{code}"'))
def then_pending(ctx, n, code):
    pending = ctx["data"]["pending"]
    assert len(pending) == n and {p["code"] for p in pending} == {code}


def _stage(ctx, sid):
    return next(s for s in ctx["data"]["pipeline"]["stages"] if s["id"] == sid)


@then(parsers.parse('流水線 "{sid}" 的數量應為 {n:d}'))
def then_stage_value(ctx, sid, n):
    assert _stage(ctx, sid)["value"] == n


@then(parsers.parse('流水線 "gate" 的通過數應為 {n:d}'))
def then_gate(ctx, n):
    assert _stage(ctx, "gate")["passed"] == n


@then(parsers.parse("每個關鍵字在第 {pos:d} 名的預估收益應等於引擎計算結果"))
def then_revenue(ctx, pos):
    engine = {k.term: forecast(k, position=pos) for k in load_keywords_csv(ctx["keywords_path"])}
    for kw in ctx["data"]["revenue"]["keywords"]:
        point = kw["curve"][pos - 1]
        assert point["pos"] == pos
        assert point["ad"] + point["aff"] == pytest.approx(engine[kw["term"]].total, rel=1e-6)


@then(parsers.parse('收益資料應同時有 "{a}" 與 "{b}"'))
def then_currencies(ctx, a, b):
    assert {k["currency"] for k in ctx["data"]["revenue"]["keywords"]} == {a, b}


@then("收益資料應標示為範例數值")
def then_example(ctx):
    assert ctx["data"]["revenue"]["example"] is True
