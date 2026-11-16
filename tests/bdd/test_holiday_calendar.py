import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md, write_project
from seoengine.site import BuildError, build_site

scenarios("../../features/holiday_calendar.feature")


@given(parsers.parse('一個新的網站專案，網址為 "{url}"'))
def given_project(ctx, tmp_path, url):
    ctx["project"] = write_project(tmp_path / "site", base_url=url)


@given(parsers.parse("專案有日本假日資料，{year:d} 年包含:"))
def given_jp_data(ctx, year, datatable):
    header, *rows = datatable
    holidays = [dict(zip(header, row)) for row in rows]
    data = {"country": "Japan", "country_zh": "日本", "code": "jp", "weekend": ["sat", "sun"], "holidays": holidays}
    path = ctx["project"] / "data" / "holidays"
    path.mkdir(parents=True)
    (path / "jp.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@given(parsers.parse('專案中有一篇英文文章 "{slug}" 內文含短碼 "{code}"'))
def given_en_article(ctx, slug, code):
    md = article_md(slug, "japan public holidays", lang="en", extra=code)
    (ctx["project"] / "content" / f"{slug}.md").write_text(md, encoding="utf-8")


@given(parsers.parse('專案中有一篇中文文章 "{slug}" 內文含短碼 "{code}"'))
def given_zh_article(ctx, slug, code):
    md = article_md(slug, "日本連假", extra=code)
    (ctx["project"] / "content" / f"{slug}.md").write_text(md, encoding="utf-8")


@when("我建置網站")
def when_build(ctx):
    ctx["result"] = build_site(ctx["project"])
    ctx["out"] = ctx["result"].out_dir


@when("我嘗試建置網站")
def when_try_build(ctx):
    try:
        build_site(ctx["project"])
    except BuildError as exc:
        ctx["error"] = exc


@then(parsers.parse('建置應失敗，訊息包含 "{text}"'))
def then_build_failed(ctx, text):
    assert "error" in ctx and text in str(ctx["error"])


@when(parsers.parse('我在 "{day}" 建置網站'))
def when_build_on(ctx, day):
    import datetime as dt
    ctx["result"] = build_site(ctx["project"], today=dt.date.fromisoformat(day))
    ctx["out"] = ctx["result"].out_dir
