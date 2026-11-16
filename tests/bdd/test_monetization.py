import re

from pytest_bdd import given, parsers, scenarios, then, when

from seoengine.monetize import (
    AD_MARKER,
    AdConfig,
    MonetizeError,
    Offer,
    expand_shortcodes,
    inject_ads,
    redirect_page,
)

scenarios("../../features/monetization.feature")


@given(parsers.parse('已登記聯盟商品 "{oid}" 名稱為 "{name}" 連結為 "{url}"'))
def given_offer(ctx, oid, name, url):
    ctx["offers"] = {oid: Offer(id=oid, name=name, url=url)}


@when(parsers.parse('我展開短碼 "{text}"'))
def when_expand(ctx, text):
    try:
        ctx["output"], ctx["used"] = expand_shortcodes(text, ctx["offers"])
    except MonetizeError as exc:
        ctx["error"] = exc


@when(parsers.parse('我產生 "{oid}" 的跳轉頁'))
def when_redirect(ctx, oid):
    ctx["output"] = redirect_page(ctx["offers"][oid])


@then(parsers.re(r"輸出應包含 (['\"])(?P<text>.*)\1"))
def then_contains(ctx, text):
    assert text in ctx["output"]


@then(parsers.re(r"輸出不應包含 (['\"])(?P<text>.*)\1"))
def then_not_contains(ctx, text):
    assert text not in ctx["output"]


@then(parsers.parse('使用到的商品應為 "{oid}"'))
def then_used(ctx, oid):
    assert ctx["used"] == {oid}


@then(parsers.parse('應拋出變現錯誤，訊息包含 "{text}"'))
def then_error(ctx, text):
    assert "error" in ctx and text in str(ctx["error"])


@given(parsers.re(r'AdSense 設定 client 為 "(?P<client>[^"]*)" 上限 (?P<max_ads>\d+) 則、間隔 (?P<gap>\d+) 字'))
def given_adsense(ctx, client, max_ads, gap):
    ctx["ads"] = AdConfig(client=client, slot="111", max_ads=int(max_ads), min_words_between=int(gap))


@given(parsers.parse("一段有 {sections:d} 個 H2 段落、每段 {words:d} 字的文章 HTML"))
def given_html(ctx, sections, words):
    ctx["html"] = "".join(
        f"<h2>第{i + 1}節</h2>\n<p>{'測' * words}</p>\n" for i in range(sections)
    )


@when("我插入廣告版位")
def when_inject(ctx):
    ctx["output"] = inject_ads(ctx["html"], ctx["ads"])


@then(parsers.parse("應插入 {n:d} 個 AdSense 廣告單元"))
def then_ad_units(ctx, n):
    assert len(re.findall(r'<ins class="adsbygoogle"', ctx["output"])) == n


@then("每個廣告前都有高轉換版位註記")
def then_marker(ctx):
    units = ctx["output"].split('<ins class="adsbygoogle"')
    assert len(units) > 1
    for before in units[:-1]:
        assert before.rstrip().endswith(AD_MARKER)


@then("沒有使用到任何商品")
def then_nothing_used(ctx):
    assert ctx["used"] == set()
