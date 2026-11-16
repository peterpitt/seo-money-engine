from seoengine.text import display_width, slugify, strip_html, tokens, word_count


def test_slugify_ascii():
    assert slugify("Best Coffee Grinder 2026!") == "best-coffee-grinder-2026"


def test_slugify_collapses_separators():
    assert slugify("  a -- b __ c ") == "a-b-c"


def test_slugify_cjk_falls_back_to_stable_hash():
    first = slugify("磨豆機推薦")
    assert first.startswith("p-") and len(first) == 10
    assert slugify("磨豆機推薦") == first
    assert slugify("手沖咖啡") != first


def test_slugify_mixed_keeps_ascii_part():
    assert slugify("Timemore C3 磨豆機") == "timemore-c3"


def test_display_width_counts_cjk_double():
    assert display_width("abc") == 3
    assert display_width("磨豆機") == 6
    assert display_width("C3 磨豆機：") == 3 + 6 + 2


def test_word_count_mixed():
    assert word_count("I love 手沖咖啡") == 2 + 4
    assert word_count("don't stop-motion 2026") == 3
    assert word_count("，。！") == 0


def test_strip_html():
    assert strip_html("<p>Hi <b>there</b></p>") == "Hi there"
    assert strip_html("a &amp; b") == "a & b"


def test_tokens_drop_stopwords_and_build_cjk_bigrams():
    assert tokens("how to clean the grinder") == {"clean", "grinder"}
    assert tokens("磨豆機") == {"磨豆", "豆機"}
