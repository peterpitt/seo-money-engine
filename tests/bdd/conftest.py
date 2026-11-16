import pytest
from pytest_bdd import given, parsers, then

from seoengine.keywords import Keyword


@pytest.fixture
def ctx() -> dict:
    """每個場景共用的狀態容器。"""
    return {}


@given("以下關鍵字清單:")
def keyword_table(ctx, datatable):
    header, *rows = datatable
    ctx["keywords"] = [Keyword.from_mapping(dict(zip(header, row))) for row in rows]


# ---- 建置輸出檢查（網站建置、行事曆等功能共用）----
@then(parsers.parse('應產生檔案 "{rel}"'))
def then_file_exists(ctx, rel):
    assert (ctx["out"] / rel).is_file(), sorted(p.name for p in ctx["out"].iterdir())


@then(parsers.parse('不應產生檔案 "{rel}"'))
def then_file_missing(ctx, rel):
    assert not (ctx["out"] / rel).exists()


@then(parsers.re(r'"(?P<rel>[^"]+)" 應包含 ([\'"])(?P<text>.*)\2'))
def then_file_contains(ctx, rel, text):
    content = (ctx["out"] / rel).read_text(encoding="utf-8")
    assert text in content


@then(parsers.re(r'"(?P<rel>[^"]+)" 不應包含 ([\'"])(?P<text>.*)\2'))
def then_file_not_contains(ctx, rel, text):
    content = (ctx["out"] / rel).read_text(encoding="utf-8")
    assert text not in content


@then(parsers.parse('結果依序應為 "{expected}"'))
def result_in_order(ctx, expected):
    names = [getattr(item, "query", None) or getattr(item, "term") for item in ctx["result"]]
    assert names == [s.strip() for s in expected.split(",")]
