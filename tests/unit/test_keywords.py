import pytest

from seoengine.keywords import (
    Intent,
    Keyword,
    classify_intent,
    cluster_keywords,
    load_keywords_csv,
    opportunity_score,
    prioritize,
)


def test_keyword_infers_intent():
    assert Keyword("best grinder", 100, 1.0, 10).intent is Intent.COMMERCIAL


@pytest.mark.parametrize(
    "kwargs",
    [dict(volume=-1), dict(cpc=-0.1), dict(difficulty=101), dict(difficulty=-1), dict(market="jp")],
)
def test_keyword_validation(kwargs):
    base = dict(term="x", volume=1, cpc=1.0, difficulty=1)
    base.update(kwargs)
    with pytest.raises(ValueError):
        Keyword(**base)


def test_from_mapping_parses_strings_and_aliases():
    kw = Keyword.from_mapping(
        {"Keyword": " 磨豆機 推薦 ", "Volume": "1,900", "CPC": "$0.9", "KD": "18", "Market": "TW"}
    )
    assert (kw.term, kw.volume, kw.cpc, kw.difficulty, kw.market) == ("磨豆機 推薦", 1900, 0.9, 18, "tw")


def test_from_mapping_explicit_intent_wins():
    kw = Keyword.from_mapping({"keyword": "coffee", "volume": "1", "cpc": "1", "difficulty": "1", "intent": "transactional"})
    assert kw.intent is Intent.TRANSACTIONAL


def test_opportunity_score_formula():
    kw = Keyword("best grinder", 1000, 2.0, 50)  # commercial weight 1.3
    assert opportunity_score(kw) == pytest.approx(1000 * 2.0 * 1.3 * 0.25)


def test_opportunity_score_zero_when_maximum_difficulty():
    assert opportunity_score(Keyword("x", 1000, 2.0, 100)) == 0


def test_navigational_is_heavily_discounted():
    nav = Keyword("amazon login", 1000, 1.0, 10)
    info = Keyword("coffee origins", 1000, 1.0, 10)
    assert opportunity_score(nav) < opportunity_score(info)


def test_prioritize_min_volume_and_top():
    kws = [Keyword(f"best item {i}", v, 1.0, 10) for i, v in enumerate([50, 500, 5000])]
    out = prioritize(kws, min_volume=100, top=1)
    assert [k.volume for k in out] == [5000]


def test_intent_word_boundary_does_not_false_match():
    # "debt" contains no "best"; "abuy" is not "buy"
    assert classify_intent("debt payoff plan") is Intent.INFORMATIONAL
    assert classify_intent("rebuy rules") is Intent.INFORMATIONAL


def test_cluster_pillar_is_highest_score():
    kws = [
        Keyword("best coffee grinder under 100", 900, 1.4, 20),
        Keyword("best coffee grinder", 5000, 1.2, 30),
    ]
    clusters = cluster_keywords(kws)
    assert clusters[0][0].term == "best coffee grinder"


def test_load_keywords_csv(tmp_path):
    p = tmp_path / "k.csv"
    p.write_text("keyword,volume,cpc,difficulty,market\nbest grinder,100,1.5,20,us\n", encoding="utf-8")
    [kw] = load_keywords_csv(p)
    assert kw.term == "best grinder" and kw.market == "us"
