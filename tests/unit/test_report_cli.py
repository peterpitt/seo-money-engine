import pytest

from helpers import write_project
from seoengine import cli
from seoengine.report import (
    load_gsc_csv,
    parse_earnings_rows,
    parse_gsc_rows,
    render_report,
)


def test_gsc_rows_accept_english_and_chinese_headers():
    en = parse_gsc_rows([{"Top queries": "a", "Clicks": "1,200", "Impressions": "10", "CTR": "3.5%", "Position": "4.2"}])
    zh = parse_gsc_rows([{"熱門查詢": "b", "點擊": "1", "曝光": "10", "點閱率": "10%", "排名": "2"}])
    assert (en[0].query, en[0].clicks, en[0].ctr, en[0].position) == ("a", 1200, 0.035, 4.2)
    assert (zh[0].query, zh[0].ctr) == ("b", 0.10)


def test_gsc_ctr_without_percent_is_ratio():
    [s] = parse_gsc_rows([{"query": "a", "clicks": "1", "impressions": "10", "ctr": "0.1", "position": "1"}])
    assert s.ctr == pytest.approx(0.1)


def test_gsc_missing_column_raises():
    with pytest.raises(ValueError, match="impressions"):
        parse_gsc_rows([{"query": "a", "clicks": "1"}])


def test_load_gsc_csv_handles_bom(tmp_path):
    p = tmp_path / "q.csv"
    p.write_text("﻿Top queries,Clicks,Impressions,CTR,Position\na,1,10,10%,3\n", encoding="utf-8")
    assert load_gsc_csv(p)[0].query == "a"


def test_earnings_invalid_currency():
    with pytest.raises(ValueError):
        parse_earnings_rows([{"date": "2026-10-01", "page": "/", "source": "x", "amount": "1", "currency": "dollars"}])


def test_render_report_contains_sections():
    stats = parse_gsc_rows([
        {"query": "a", "clicks": "1", "impressions": "500", "ctr": "0.2%", "position": "12"},
        {"query": "b", "clicks": "2", "impressions": "900", "ctr": "0.2%", "position": "2"},
    ])
    earnings = parse_earnings_rows([{"date": "2026-10-01", "page": "/a/", "source": "adsense", "amount": "5", "currency": "USD"}])
    md = render_report(stats, earnings)
    assert "擊殺距離" in md and "點閱率落差" in md and "收益" in md
    assert "| a |" in md and "| b |" in md and "/a/" in md


def test_cli_init_build_check(tmp_path, capsys):
    root = tmp_path / "site"
    assert cli.main(["init", str(root)]) == 0
    assert (root / "site.yaml").exists() and (root / "offers.yaml").exists()
    assert cli.main(["check", str(root)]) == 0
    assert cli.main(["build", str(root)]) == 0
    assert (root / "public" / "index.html").exists()


def test_cli_init_refuses_non_empty_dir(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "file").write_text("x")
    assert cli.main(["init", str(tmp_path / "x")]) == 1


def test_cli_check_fails_on_bad_article(tmp_path):
    root = write_project(tmp_path / "p")
    (root / "content" / "bad.md").write_text("---\ntitle: T\nkeyword: zzz\n---\n在這個日新月異的時代", encoding="utf-8")
    assert cli.main(["check", str(root)]) == 1


def test_cli_brief_creates_draft(tmp_path):
    root = write_project(tmp_path / "p")
    assert cli.main(["brief", "磨豆機 推薦", "--project", str(root), "--market", "tw", "--slug", "grinder-guide"]) == 0
    text = (root / "content" / "grinder-guide.md").read_text(encoding="utf-8")
    assert "draft: true" in text and "keyword: 磨豆機 推薦" in text and "## " in text
    # 不覆蓋既有檔案
    assert cli.main(["brief", "磨豆機 推薦", "--project", str(root), "--slug", "grinder-guide"]) == 1


def test_cli_keywords_and_forecast(tmp_path, capsys):
    p = tmp_path / "k.csv"
    p.write_text("keyword,volume,cpc,difficulty,market\nbest grinder,1000,1.5,20,us\n磨豆機推薦,800,0.5,10,tw\n", encoding="utf-8")
    assert cli.main(["keywords", str(p), "--clusters"]) == 0
    out = capsys.readouterr().out
    assert "best grinder" in out and "commercial" in out
    assert cli.main(["forecast", str(p), "--position", "3"]) == 0
    out = capsys.readouterr().out
    assert "USD" in out and "TWD" in out


def test_cli_report(tmp_path):
    g = tmp_path / "g.csv"
    g.write_text("query,clicks,impressions,ctr,position\na,1,500,0.2%,12\n", encoding="utf-8")
    out = tmp_path / "r.md"
    assert cli.main(["report", "--gsc", str(g), "-o", str(out)]) == 0
    assert "擊殺距離" in out.read_text(encoding="utf-8")
