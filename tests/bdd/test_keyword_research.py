from pytest_bdd import given, parsers, scenarios, then, when

from seoengine.keywords import classify_intent, cluster_keywords, prioritize

scenarios("../../features/keyword_research.feature")


@given(parsers.parse('關鍵字 "{term}"'))
def given_term(ctx, term):
    ctx["term"] = term


@when("系統判斷搜尋意圖")
def when_classify(ctx):
    ctx["intent"] = classify_intent(ctx["term"])


@then(parsers.parse('搜尋意圖應為 "{intent}"'))
def then_intent(ctx, intent):
    assert ctx["intent"].value == intent


@when("我依錢景分數排序")
def when_prioritize(ctx):
    ctx["result"] = prioritize(ctx["keywords"])


@when(parsers.parse("我以難度上限 {max_kd:d} 排序"))
def when_prioritize_kd(ctx, max_kd):
    ctx["result"] = prioritize(ctx["keywords"], max_difficulty=max_kd)


@then(parsers.parse('第一名應為 "{term}"'))
def then_first(ctx, term):
    assert ctx["result"][0].term == term


@then(parsers.parse('"{lower}" 的排名應在 "{higher}" 之後'))
def then_rank_after(ctx, lower, higher):
    terms = [k.term for k in ctx["result"]]
    assert terms.index(lower) > terms.index(higher)


@then(parsers.parse('結果應只包含 "{term}"'))
def then_only(ctx, term):
    assert [k.term for k in ctx["result"]] == [term]


@when("我將關鍵字分群")
def when_cluster(ctx):
    ctx["clusters"] = cluster_keywords(ctx["keywords"])


@then(parsers.parse("應產生 {n:d} 個主題群"))
def then_cluster_count(ctx, n):
    assert len(ctx["clusters"]) == n


@then(parsers.parse('"{a}" 與 "{b}" 應在同一群'))
def then_same_cluster(ctx, a, b):
    for cluster in ctx["clusters"]:
        terms = {k.term for k in cluster}
        if a in terms:
            assert b in terms
            return
    raise AssertionError(f"{a} not found in any cluster")


@given("一個 Google Ads 匯出檔（UTF-16、Tab 分隔、台幣出價）:", target_fixture="export_path")
def given_planner_export(tmp_path, datatable):
    lines = ["Keyword Stats 2026-10-25", "2025年10月1日 - 2026年9月30日"] + ["\t".join(r) for r in datatable]
    path = tmp_path / "Keyword Stats.csv"
    path.write_bytes("\n".join(lines).encode("utf-16"))
    return path


@when(parsers.parse("我用匯率 {cur}={rate:f} 匯入"))
def when_import(ctx, export_path, cur, rate):
    from seoengine.keywords import load_keywords_csv
    ctx["imported"] = {k.term: k for k in load_keywords_csv(export_path, fx_to_usd={cur: rate})}


@then(parsers.parse("應匯入 {n:d} 個關鍵字"))
def then_imported_count(ctx, n):
    assert len(ctx["imported"]) == n


@then(parsers.parse('"{term}" 的市場應為 "{market}"、搜尋量約 {volume:d}'))
def then_imported_kw(ctx, term, market, volume):
    kw = ctx["imported"][term]
    assert (kw.market, kw.volume) == (market, volume)
