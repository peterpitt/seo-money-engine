import json

from helpers import article_md
from seoengine.content import parse_article
from seoengine.linking import LinkTarget, auto_internal_links
from seoengine.schema import article_schema, breadcrumb_schema, faq_schema

TARGETS = [
    LinkTarget(keyword="磨豆機推薦", url="/grinder/", slug="grinder"),
    LinkTarget(keyword="手沖咖啡", url="/pour-over/", slug="pour-over"),
    LinkTarget(keyword="best grinder", url="/best/", slug="best"),
]


def test_links_first_occurrence_only():
    html, linked = auto_internal_links("<p>磨豆機推薦 和 磨豆機推薦</p>", "x", TARGETS)
    assert html.count('href="/grinder/"') == 1
    assert linked == ["grinder"]


def test_does_not_link_self():
    html, linked = auto_internal_links("<p>磨豆機推薦</p>", "grinder", TARGETS)
    assert "href" not in html and linked == []


def test_skips_headings_and_existing_links():
    src = '<h2>磨豆機推薦</h2><p><a href="/x/">手沖咖啡</a></p>'
    html, linked = auto_internal_links(src, "x", TARGETS)
    assert html == src and linked == []


def test_case_insensitive_latin_preserves_original_text():
    html, _ = auto_internal_links("<p>The Best Grinder ever</p>", "x", TARGETS)
    assert '<a href="/best/">Best Grinder</a>' in html


def test_latin_requires_word_boundary():
    html, linked = auto_internal_links("<p>bestgrinders</p>", "x", TARGETS)
    assert linked == []


def test_max_links_respected():
    html, linked = auto_internal_links("<p>磨豆機推薦 手沖咖啡 best grinder</p>", "x", TARGETS, max_links=2)
    assert len(linked) == 2


def test_longer_keyword_wins_overlap():
    targets = [LinkTarget("咖啡", "/a/", "a"), LinkTarget("手沖咖啡", "/b/", "b")]
    html, linked = auto_internal_links("<p>手沖咖啡</p>", "x", targets)
    assert linked == ["b"]


def test_article_schema():
    a = parse_article(article_md("g", "磨豆機推薦"))
    data = json.loads(article_schema(a, "https://s.example.com/g/", "站名", "Tsung"))
    assert data["@type"] == "Article"
    assert data["headline"] == a.title
    assert data["inLanguage"] == "zh-TW"
    assert data["author"]["name"] == "Tsung"
    assert data["datePublished"] == "2026-10-01"


def test_faq_schema():
    assert faq_schema([]) is None
    data = json.loads(faq_schema([{"q": "Q1", "a": "A1"}]))
    assert data["mainEntity"][0]["acceptedAnswer"]["text"] == "A1"


def test_breadcrumb_schema_positions():
    data = json.loads(breadcrumb_schema([("首頁", "https://s/"), ("文章", "https://s/a/")]))
    assert [i["position"] for i in data["itemListElement"]] == [1, 2]


def test_article_schema_author_links_to_about_page():
    a = parse_article(article_md("g", "磨豆機推薦"))
    data = json.loads(article_schema(a, "https://s.example.com/g/", "站名", "Tsung",
                                     author_url="https://s.example.com/about/zh-tw/"))
    assert data["author"] == {"@type": "Person", "name": "Tsung", "url": "https://s.example.com/about/zh-tw/"}


def test_article_schema_editorial_team_is_an_organization_not_a_person():
    a = parse_article(article_md("g", "best grinder", lang="en"))
    data = json.loads(article_schema(a, "https://s.example.com/g/", "Site", "Site Editorial",
                                     author_url="https://s.example.com/about/", author_type="organization"))
    assert data["author"]["@type"] == "Organization" and data["author"]["name"] == "Site Editorial"


def test_article_with_its_own_byline_is_always_a_person():
    a = parse_article(article_md("g", "best grinder", lang="en").replace("slug: g\n", "slug: g\nauthor: Jane Doe\n"))
    data = json.loads(article_schema(a, "https://s.example.com/g/", "Site", "Site Editorial", author_type="organization"))
    assert data["author"]["@type"] == "Person" and data["author"]["name"] == "Jane Doe"
