import xml.etree.ElementTree as ET

import pytest
import yaml

from helpers import article_md, write_project
from seoengine.content import ContentError
from seoengine.site import BuildError, SiteConfig, build_site


@pytest.fixture
def project(tmp_path):
    root = write_project(tmp_path / "p")
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦"), encoding="utf-8")
    return root


def test_site_config_defaults_and_trailing_slash(tmp_path):
    root = write_project(tmp_path / "c", base_url="https://x.example.com/")
    cfg = SiteConfig.load(root / "site.yaml")
    assert cfg.base_url == "https://x.example.com"
    assert cfg.quality.min_words == 120
    assert cfg.adsense.enabled is False


def test_site_config_requires_https_base_url(tmp_path):
    root = write_project(tmp_path / "c", base_url="example.com")
    with pytest.raises(BuildError, match="base_url"):
        SiteConfig.load(root / "site.yaml")


def test_sitemap_is_valid_xml_with_lastmod(project):
    out = build_site(project).out_dir
    tree = ET.parse(out / "sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in tree.findall(".//s:loc", ns)]
    assert "https://coffee.example.com/" in locs and "https://coffee.example.com/a/" in locs
    assert tree.findall(".//s:lastmod", ns)


def test_feed_is_valid_rss(project):
    out = build_site(project).out_dir
    root = ET.parse(out / "feed.xml").getroot()
    assert root.tag == "rss"
    assert root.find("./channel/item/link").text == "https://coffee.example.com/a/"


def test_index_lists_published_articles(project):
    out = build_site(project).out_dir
    assert 'href="/a/"' in (out / "index.html").read_text(encoding="utf-8")


def test_article_page_essentials(project):
    html = (build_site(project).out_dir / "a" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="zh-TW">' in html
    assert html.count("<h1") == 1
    assert '<meta name="description"' in html
    assert 'property="og:title"' in html
    assert '<meta name="viewport"' in html
    assert '"@type": "BreadcrumbList"' in html


def test_force_publishes_failing_articles(project):
    (project / "content" / "bad.md").write_text(
        article_md("bad", "磨豆機保養", extra="在這個日新月異的時代。"), encoding="utf-8"
    )
    result = build_site(project, force=True)
    assert (result.out_dir / "bad" / "index.html").exists()
    assert "bad" in result.published


def test_duplicate_slug_fails(project):
    (project / "content" / "b.md").write_text(article_md("a", "手沖咖啡教學"), encoding="utf-8")
    with pytest.raises(BuildError, match="duplicate"):
        build_site(project)


def test_unknown_offer_fails_build(project):
    (project / "content" / "c.md").write_text(article_md("c", "手沖咖啡教學", extra="[[cta:ghost]]"), encoding="utf-8")
    with pytest.raises(BuildError, match="ghost"):
        build_site(project)


def test_english_article_gets_english_monetization_labels(project):
    (project / "offers.yaml").write_text("g1:\n  name: G1\n  url: https://a.brewlab.tw\n", encoding="utf-8")
    (project / "content" / "en.md").write_text(
        article_md("en", "best coffee grinder", lang="en", extra="[[compare:g1]]"), encoding="utf-8"
    )
    html = (build_site(project).out_dir / "en" / "index.html").read_text(encoding="utf-8")
    assert "<th>Product</th>" in html and "<th>商品</th>" not in html


def test_rebuild_removes_stale_pages(project):
    build_site(project)
    (project / "content" / "a.md").unlink()
    (project / "content" / "z.md").write_text(article_md("z", "手沖咖啡教學"), encoding="utf-8")
    out = build_site(project).out_dir
    assert not (out / "a").exists()


def test_ga4_snippet_and_affiliate_click_tracking(tmp_path):
    root = write_project(tmp_path / "g", analytics={"ga4": "G-TEST123"})
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦"), encoding="utf-8")
    html = (build_site(root).out_dir / "a" / "index.html").read_text(encoding="utf-8")
    assert "G-TEST123" in html and "affiliate_click" in html


def test_quality_report_written(project):
    out = build_site(project).out_dir
    data = yaml.safe_load((project / "quality-report.json").read_text(encoding="utf-8"))
    assert data["a"]["passed"] is True
    assert not (out / "quality-report.json").exists()


def test_check_public_blocks_private_files(tmp_path):
    from seoengine.deploy import DeployError, check_public
    (tmp_path / "ok.html").write_text("x")
    check_public(tmp_path)
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "google-ads.yaml").write_text("x")
    with pytest.raises(DeployError, match="google-ads"):
        check_public(tmp_path)


def test_deploy_requires_project_name(tmp_path):
    from seoengine.deploy import DeployError, deploy_site
    root = write_project(tmp_path / "d", base_url="https://asusucloud.site")
    with pytest.raises(DeployError, match="cloudflare_project"):
        deploy_site(root, runner=lambda c: 0)


def test_deploy_reports_wrangler_failure(tmp_path):
    from seoengine.deploy import DeployError, deploy_site
    root = write_project(tmp_path / "d", base_url="https://asusucloud.site", deploy={"cloudflare_project": "asusucloud"})
    with pytest.raises(DeployError, match="wrangler login"):
        deploy_site(root, runner=lambda c: 1)


def test_cli_deploy_refuses_example_domain(project, capsys):
    from seoengine import cli
    assert cli.main(["deploy", str(project)]) == 1
    assert "base_url" in capsys.readouterr().err


# ---------------------------------------------------------------- 子網域姊妹站（同一個品牌的其他網站）
NETWORK = [{"name": "假日行事曆", "url": "https://brand.example"},
           {"name": "音樂", "url": "https://music.brand.example"},
           {"name": "公益小幫手", "url": "https://app.brand.example/"}]


def _footer(html):
    return html.split('<footer class="site-footer">', 1)[1].split("</footer>", 1)[0]


def test_footer_links_sister_sites_but_not_itself(tmp_path):
    root = write_project(tmp_path / "d", base_url="https://brand.example", site={"network": NETWORK})
    out = build_site(root).out_dir
    footer = _footer((out / "index.html").read_text(encoding="utf-8"))
    assert 'href="https://music.brand.example"' in footer and "音樂" in footer
    assert 'href="https://app.brand.example"' in footer
    assert 'href="https://brand.example"' not in footer           # 不連到自己


def test_subdomain_site_links_back_to_the_main_site(tmp_path):
    root = write_project(tmp_path / "m", base_url="https://music.brand.example", site={"network": NETWORK})
    footer = _footer((build_site(root).out_dir / "index.html").read_text(encoding="utf-8"))
    assert 'href="https://brand.example"' in footer and 'href="https://music.brand.example"' not in footer


def test_no_network_means_no_sister_links(tmp_path):
    root = write_project(tmp_path / "d", base_url="https://brand.example")
    assert "site-network" not in (build_site(root).out_dir / "index.html").read_text(encoding="utf-8")


def test_network_urls_must_be_https(tmp_path):
    root = write_project(tmp_path / "d", base_url="https://brand.example",
                         site={"network": [{"name": "x", "url": "http://music.brand.example"}]})
    from seoengine.site import BuildError
    with pytest.raises(BuildError, match="network"):
        SiteConfig.load(root / "site.yaml")


@pytest.mark.parametrize("url", ["https://your-domain.example", "https://music.your-domain.example",
                                 "https://site.test", "https://foo.invalid", "https://example.com",
                                 "https://shop.example.org", "https://app.localhost"])
def test_deploy_refuses_placeholder_domains_before_calling_wrangler(tmp_path, url):
    from seoengine.deploy import DeployError, deploy_site
    root = write_project(tmp_path / "d", base_url=url, deploy={"cloudflare_project": "asusu-calendar"})
    called = []
    with pytest.raises(DeployError, match="base_url"):
        deploy_site(root, runner=lambda c: called.append(c) or 0)
    assert not called


def test_build_publishes_no_placeholder_affiliate_pages(tmp_path):
    root = write_project(tmp_path / "d", base_url="https://brand.tw")
    (root / "offers.yaml").write_text("demo:\n  name: 示範訂房\n  url: https://example.com/aff/demo\n", encoding="utf-8")
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦", extra="[[cta:demo]]"), encoding="utf-8")
    out = build_site(root).out_dir
    assert not (out / "go" / "demo").exists()
    assert "example.com" not in (out / "a" / "index.html").read_text(encoding="utf-8")


def test_deploy_refuses_pages_that_still_link_to_placeholder_domains(tmp_path):
    from seoengine.deploy import DeployError, check_public
    (tmp_path / "go" / "x").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<p>ok</p>", encoding="utf-8")
    (tmp_path / "go" / "x" / "index.html").write_text('<meta http-equiv="refresh" content="0; url=https://example.com/aff/x">',
                                                       encoding="utf-8")
    with pytest.raises(DeployError, match="example.com"):
        check_public(tmp_path)


def test_deploy_allows_reserved_domains_inside_text_that_is_not_a_link(tmp_path):
    from seoengine.deploy import check_public
    (tmp_path / "index.html").write_text("<p>例如 example.com 這種網址</p>", encoding="utf-8")
    check_public(tmp_path)


# ---------------------------------------------------------------- Windows：npx 其實是 npx.cmd
def _deployable(tmp_path):
    return write_project(tmp_path / "d", base_url="https://brand.tw", deploy={"cloudflare_project": "asusu-calendar"})


def test_deploy_runs_npx_by_its_full_path_so_windows_finds_npx_cmd(tmp_path, monkeypatch):
    from seoengine import deploy
    monkeypatch.setattr(deploy.shutil, "which", lambda n: r"C:\Program Files\nodejs\npx.cmd" if n == "npx" else None)
    seen = []
    deploy.deploy_site(_deployable(tmp_path), runner=lambda c: seen.append(c) or 0)
    assert seen[0][0] == r"C:\Program Files\nodejs\npx.cmd" and seen[0][1:4] == ["wrangler", "pages", "deploy"]


def test_deploy_explains_when_node_is_missing(tmp_path, monkeypatch):
    from seoengine import deploy
    monkeypatch.setattr(deploy.shutil, "which", lambda n: None)
    called = []
    with pytest.raises(deploy.DeployError, match="Node.js"):
        deploy.deploy_site(_deployable(tmp_path), runner=lambda c: called.append(c) or 0)
    assert not called


def test_deploy_turns_a_launch_failure_into_a_readable_error(tmp_path, monkeypatch):
    from seoengine import deploy
    monkeypatch.setattr(deploy.shutil, "which", lambda n: "/usr/bin/npx")

    def boom(cmd):
        raise FileNotFoundError(2, "系統找不到指定的檔案。")
    with pytest.raises(deploy.DeployError, match="Node.js"):
        deploy.deploy_site(_deployable(tmp_path), runner=boom)


def test_cli_deploy_never_shows_a_traceback(tmp_path, monkeypatch, capsys):
    from seoengine import cli, deploy
    monkeypatch.setattr(deploy.shutil, "which", lambda n: None)
    assert cli.main(["deploy", str(_deployable(tmp_path))]) == 1
    assert "Node.js" in capsys.readouterr().err


# ---------------------------------------------------------------- 審核修正：列表日期、署名

def test_index_shows_date_and_author_for_every_article(project):
    import re
    out = build_site(project).out_dir
    html = (out / "index.html").read_text(encoding="utf-8")
    items = re.findall(r"<li>(.*?)</li>", html.split('class="post-list"', 1)[1].split("</ul>", 1)[0], re.S)
    assert items and all('<time datetime="2026-10-01">2026-10-01</time>' in i for i in items)


def test_article_byline_links_to_about_and_shows_published_date_when_updated(tmp_path):
    root = write_project(tmp_path / "s")
    md = article_md("g", "磨豆機推薦").replace("date: '2026-10-01'\n", "date: '2026-10-01'\nupdated: '2026-11-16'\n")
    assert "updated:" in md
    (root / "content" / "g.md").write_text(md, encoding="utf-8")
    html = (build_site(root).out_dir / "g" / "index.html").read_text(encoding="utf-8")
    assert '<a rel="author" href="/about/zh-tw/">Tsung</a>' in html
    assert '<time datetime="2026-11-16">2026-11-16</time>' in html and '<time datetime="2026-10-01">2026-10-01</time>' in html
    assert '"url": "https://coffee.example.com/about/zh-tw/"' in html


def test_site_author_type_is_read_from_config_and_validated(tmp_path):
    root = write_project(tmp_path / "s", site={"author_type": "organization"})
    assert SiteConfig.load(root / "site.yaml").author_type == "organization"
    assert SiteConfig.load(write_project(tmp_path / "d") / "site.yaml").author_type == "person"
    bad = write_project(tmp_path / "b", site={"author_type": "robot"})
    with pytest.raises(BuildError, match="author_type"):
        SiteConfig.load(bad / "site.yaml")


def test_assets_are_cache_busted_by_style_content_hash(project):
    import hashlib, re
    from seoengine.site import TEMPLATES
    v = hashlib.sha1((TEMPLATES / "style.css").read_bytes()).hexdigest()[:8]
    out = build_site(project).out_dir
    for rel in ("a/index.html", "index.html"):
        html = (out / rel).read_text(encoding="utf-8")
        assert f'href="/style.css?v={v}"' in html, rel
