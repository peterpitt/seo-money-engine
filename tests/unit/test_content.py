import datetime as dt

import pytest

from helpers import article_md
from seoengine.content import ContentError, extract_headings, load_articles, parse_article, render_markdown


def test_parse_article_fields():
    a = parse_article(article_md("grinder", "磨豆機推薦", faq=2, translation_key="g"))
    assert a.slug == "grinder"
    assert a.keyword == "磨豆機推薦"
    assert a.lang == "zh-TW" and a.market == "tw"
    assert a.date == dt.date(2026, 10, 1)
    assert a.updated == a.date
    assert len(a.faq) == 2 and set(a.faq[0]) == {"q", "a"}
    assert a.translation_key == "g"
    assert a.draft is False


def test_parse_article_requires_front_matter():
    with pytest.raises(ContentError):
        parse_article("# no front matter")


@pytest.mark.parametrize("missing", ["title", "keyword"])
def test_parse_article_required_fields(missing):
    md = f"---\ntitle: T\nkeyword: k\ndescription: d\n---\nbody".replace(f"{missing}:", "x_ignored:")
    with pytest.raises(ContentError, match=missing):
        parse_article(md, source="post.md")


def test_slug_defaults_from_keyword_then_title():
    a = parse_article("---\ntitle: Best Grinder Guide\nkeyword: best coffee grinder\n---\nbody")
    assert a.slug == "best-coffee-grinder"


def test_invalid_slug_rejected():
    with pytest.raises(ContentError):
        parse_article("---\ntitle: T\nkeyword: k\nslug: Bad Slug!\n---\nbody")


def test_render_markdown_tables_and_heading_ids():
    html = render_markdown("## Hello World\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert '<h2 id="hello-world">' in html
    assert "<table>" in html


def test_extract_headings():
    html = render_markdown("## One\n\n### Sub\n\n## Two\n")
    assert [(lvl, text) for lvl, _id, text in extract_headings(html)] == [(2, "One"), (3, "Sub"), (2, "Two")]


def test_load_articles_skips_underscore_files(tmp_path):
    (tmp_path / "a.md").write_text(article_md("a", "磨豆機推薦"), encoding="utf-8")
    (tmp_path / "_template.md").write_text("junk", encoding="utf-8")
    assert [a.slug for a in load_articles(tmp_path)] == ["a"]
