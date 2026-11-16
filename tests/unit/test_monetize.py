import pytest

from seoengine.monetize import (
    AD_MARKER,
    AdConfig,
    MonetizeError,
    Offer,
    ads_txt,
    disclosure_html,
    expand_shortcodes,
    inject_ads,
    load_offers,
    redirect_page,
)

OFFERS = {
    "h1": Offer(id="h1", name="Brewlab H1", url="https://aff.brewlab.tw/h1", price="NT$2,490", rating=4.5,
                pros=["輕巧"], cons=["容量小"], cta="查看最新價格"),
    "e2": Offer(id="e2", name="Brewlab E2 <Pro>", url="https://aff.brewlab.tw/e2", price="NT$6,900"),
}


def test_offer_link_custom_text():
    out, used = expand_shortcodes("[[offer:h1|點我看價格]]", OFFERS)
    assert ">點我看價格</a>" in out and used == {"h1"}


def test_offer_names_are_html_escaped():
    out, _ = expand_shortcodes("[[offer:e2]]", OFFERS)
    assert "Brewlab E2 &lt;Pro&gt;" in out


def test_cta_box():
    out, used = expand_shortcodes("[[cta:h1]]", OFFERS)
    assert 'class="cta-box"' in out and "查看最新價格" in out and "NT$2,490" in out
    assert used == {"h1"}


def test_compare_table_lists_all_offers_and_attrs():
    out, used = expand_shortcodes("[[compare:h1,e2]]", OFFERS)
    assert "<table" in out and out.count('href="/go/') == 2
    assert "輕巧" in out and "容量小" in out
    assert used == {"h1", "e2"}


def test_compare_table_headers_follow_article_language():
    zh, _ = expand_shortcodes("[[compare:h1]]", OFFERS, lang="zh-TW")
    en, _ = expand_shortcodes("[[compare:e2]]", OFFERS, lang="en")
    assert "<th>商品</th>" in zh
    assert "<th>Product</th>" in en and "商品" not in en


def test_compare_cells_carry_labels_for_mobile_card_layout():
    out, _ = expand_shortcodes("[[compare:h1]]", OFFERS, lang="en")
    assert 'data-label="Price"' in out and 'data-label="Pros"' in out


def test_default_cta_text_follows_language():
    bare = {"x": Offer(id="x", name="X", url="https://a.brewlab.tw")}
    assert "Check price" in expand_shortcodes("[[cta:x]]", bare, lang="en")[0]
    assert "查看最新價格" in expand_shortcodes("[[cta:x]]", bare, lang="zh-TW")[0]


def test_compare_unknown_offer_raises():
    with pytest.raises(MonetizeError, match="nope"):
        expand_shortcodes("[[compare:h1,nope]]", OFFERS)


def test_offer_id_validation():
    with pytest.raises(ValueError):
        Offer(id="Bad ID", name="x", url="https://x")
    with pytest.raises(ValueError):
        Offer(id="ok", name="x", url="javascript:alert(1)")


def test_load_offers(tmp_path):
    p = tmp_path / "offers.yaml"
    p.write_text("h1:\n  name: H1\n  url: https://a.brewlab.tw\n  pros: [a]\n", encoding="utf-8")
    offers = load_offers(p)
    assert offers["h1"].pros == ["a"]
    assert load_offers(tmp_path / "missing.yaml") == {}


def test_redirect_page_escapes_url_and_redirects():
    page = redirect_page(Offer(id="q", name="Q", url="https://a.brewlab.tw/?a=1&b=2"))
    assert 'http-equiv="refresh"' in page
    assert "a=1&amp;b=2" in page


def test_disclosure_language():
    assert "聯盟" in disclosure_html("zh-TW")
    assert "affiliate" in disclosure_html("en").lower()


def test_ads_txt():
    assert ads_txt("ca-pub-42") == "google.com, pub-42, DIRECT, f08c47fec0942fa0\n"
    assert ads_txt("") is None


def test_inject_ads_never_before_first_heading_without_enough_words():
    html = "<h2>A</h2><p>short</p><h2>B</h2><p>short</p>"
    cfg = AdConfig(client="ca-pub-1", slot="1", max_ads=3, min_words_between=50)
    assert inject_ads(html, cfg).count("adsbygoogle\"") == 0


def test_inject_ads_disabled_still_marks_slots():
    html = "".join(f"<h2>S{i}</h2><p>{'字' * 60}</p>" for i in range(3))
    out = inject_ads(html, AdConfig(client="", max_ads=3, min_words_between=50))
    assert out.count(AD_MARKER) == 2
    assert "adsbygoogle" not in out


# ---------------------------------------------------------------- 範例網址的商品不上線
import pytest as _pytest

from seoengine.domains import is_placeholder_url


@_pytest.mark.parametrize("url, placeholder", [
    ("https://example.com/aff/x", True), ("https://aff.example.com/x", True), ("https://shop.example.org", True),
    ("https://a.test/x", True), ("https://x.invalid", True), ("http://localhost:8000/x", True),
    ("https://www.klook.com/zh-TW/?aid=1", False), ("https://www.example-travel.com/", False),
    ("https://notexample.com/", False),
])
def test_placeholder_url_detection(url, placeholder):
    assert is_placeholder_url(url) is placeholder


def test_compare_table_skips_placeholder_offers_but_keeps_real_ones():
    offers = {"real": Offer(id="real", name="Real", url="https://www.klook.com/?aid=1"),
              "demo": Offer(id="demo", name="Demo", url="https://example.com/aff/demo")}
    html, used = expand_shortcodes("[[compare:real,demo]]", offers)
    assert used == {"real"} and "/go/real/" in html and "/go/demo/" not in html


def test_unknown_offer_still_fails_even_with_placeholders_present():
    offers = {"demo": Offer(id="demo", name="Demo", url="https://example.com/aff/demo")}
    with _pytest.raises(MonetizeError, match="ghost"):
        expand_shortcodes("[[cta:ghost]]", offers)
