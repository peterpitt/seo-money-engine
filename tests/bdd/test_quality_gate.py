from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md
from seoengine.content import parse_article
from seoengine.quality import QualityConfig, check_article

scenarios("../../features/quality_gate.feature")


@given(parsers.parse("品質門檻為最少 {n:d} 字"))
def given_threshold(ctx, n):
    ctx["config"] = QualityConfig(min_words=n)


@given(parsers.parse('一篇目標關鍵字為 "{keyword}" 的合格文章'))
def given_good_article(ctx, keyword):
    ctx["article"] = parse_article(article_md("test-post", keyword))


@given(parsers.parse('文章內文加入 "{text}"'))
def given_append(ctx, text):
    ctx["article"].body_md += f"\n\n{text}\n"


@given(parsers.parse('文章標題改為 "{title}"'))
def given_title(ctx, title):
    ctx["article"].title = title


@given("文章內文只剩一句話")
def given_thin(ctx):
    ctx["article"].body_md = f"{ctx['article'].keyword}就看這篇。\n"


@given(parsers.parse("文章內文加入一段 {n:d} 字的長段落"))
def given_long_paragraph(ctx, n):
    ctx["article"].body_md += "\n\n" + ("研磨均勻度決定萃取品質" * 40)[:n] + "\n"


@when("我執行品質檢查")
def when_check(ctx):
    ctx["report"] = check_article(ctx["article"], config=ctx["config"])


@then("檢查結果應為通過")
def then_pass(ctx):
    assert ctx["report"].passed, ctx["report"].errors


@then("檢查結果應為不通過")
def then_fail(ctx):
    assert not ctx["report"].passed


@then(parsers.parse("品質分數應不低於 {n:d}"))
def then_score(ctx, n):
    assert ctx["report"].score >= n, ctx["report"].issues


@then(parsers.parse('錯誤應包含規則 "{rule}"'))
def then_error_rule(ctx, rule):
    assert rule in {i.rule for i in ctx["report"].errors}, ctx["report"].issues


@then(parsers.parse('警告應包含規則 "{rule}"'))
def then_warning_rule(ctx, rule):
    assert rule in {i.rule for i in ctx["report"].warnings}, ctx["report"].issues
