from pytest_bdd import given, parsers, scenarios, when

from helpers import article_md, write_project
from seoengine.site import build_site

scenarios("../../features/legal_pages.feature")


@given(parsers.parse('一個網站專案，網址為 "{url}"，啟用 AdSense 與 GA4'))
def given_project(ctx, tmp_path, url):
    root = write_project(tmp_path / "site", base_url=url,
                         adsense={"client": "ca-pub-1234567890", "slot": "1"}, analytics={"ga4": "G-TEST1"})
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦"), encoding="utf-8")
    ctx["project"] = root


@when("我建置網站")
def when_build(ctx):
    ctx["out"] = build_site(ctx["project"]).out_dir
