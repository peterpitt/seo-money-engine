import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md, write_project
from seoengine.site import build_site

scenarios("../../features/site_build.feature")


def _write(ctx, slug, md):
    (ctx["project"] / "content" / f"{slug}.md").write_text(md, encoding="utf-8")


@given(parsers.parse('一個新的網站專案，網址為 "{url}"'))
def given_project(ctx, tmp_path, url):
    ctx["project"] = write_project(tmp_path / "site", base_url=url)


@given(parsers.parse('已登記聯盟商品 "{oid}" 名稱為 "{name}" 連結為 "{url}"'))
def given_offer(ctx, oid, name, url):
    data = {oid: {"name": name, "url": url, "network": "demo"}}
    (ctx["project"] / "offers.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )


@given(parsers.parse('AdSense 發布商 ID 為 "{client}"'))
def given_adsense(ctx, client):
    path = ctx["project"] / "site.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["adsense"]["client"] = client
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"'))
def given_article(ctx, slug, keyword):
    _write(ctx, slug, article_md(slug, keyword))


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"，並附 {n:d} 則常見問答'))
def given_article_faq(ctx, slug, keyword, n):
    _write(ctx, slug, article_md(slug, keyword, faq=n))


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"，內文引用商品 "{oid}"'))
def given_article_offer(ctx, slug, keyword, oid):
    _write(ctx, slug, article_md(slug, keyword, extra=f"[[cta:{oid}]]"))


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"，內文提到 "{mention}"'))
def given_article_mention(ctx, slug, keyword, mention):
    _write(ctx, slug, article_md(slug, keyword, mention=mention))


@given(parsers.parse('專案中有一篇合格文章 "{slug}" 關鍵字為 "{keyword}"，翻譯群組為 "{key}"'))
def given_article_translation(ctx, slug, keyword, key):
    _write(ctx, slug, article_md(slug, keyword, translation_key=key))


@given(parsers.parse('專案中有一篇英文合格文章 "{slug}" 關鍵字為 "{keyword}"，翻譯群組為 "{key}"'))
def given_en_article(ctx, slug, keyword, key):
    _write(ctx, slug, article_md(slug, keyword, lang="en", translation_key=key))


@given(parsers.parse('專案中有一篇含 AI 套話的文章 "{slug}"'))
def given_bad_article(ctx, slug):
    _write(ctx, slug, article_md(slug, "磨豆機保養", extra="在這個日新月異的時代，保養變得很重要。"))


@given(parsers.parse('專案中有一篇草稿 "{slug}"'))
def given_draft(ctx, slug):
    _write(ctx, slug, article_md(slug, "磨豆機刻度", draft=True))


@when("我建置網站")
def when_build(ctx):
    ctx["result"] = build_site(ctx["project"])
    ctx["out"] = ctx["result"].out_dir


@then(parsers.parse('建置結果應記錄 "{slug}" 因品質閘門被略過'))
def then_skipped(ctx, slug):
    assert slug in ctx["result"].skipped
    assert "quality" in ctx["result"].skipped[slug]


@then("文章列表的每一篇都應顯示日期與作者")
def then_list_has_dates_and_author(ctx):
    import re
    page = (ctx["out"] / "index.html").read_text(encoding="utf-8")
    items = re.findall(r"<li>(.*?)</li>", page.split('class="post-list"', 1)[1].split("</ul>", 1)[0], re.S)
    assert items
    for item in items:
        assert re.search(r'<time datetime="\d{4}-\d{2}-\d{2}">', item), item
        assert "Tsung" in item, item
