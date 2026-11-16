"""關鍵字檔的各種實際格式：Google Ads 匯出（UTF-16 + Tab）、Excel 另存（Big5）、自家格式。"""
import pytest

from seoengine.keywords import load_keywords_csv, parse_volume

OURS = "keyword,volume,cpc,difficulty,market\n日本黃金週,30000,0.07,20,tw\n"

# Google Ads 關鍵字規劃工具「已保存的關鍵字」匯出：前兩行是標題與日期，第三行才是欄位名
PLANNER_EN = (
    "Keyword Stats 2026-10-25 at 22_29_27\n"
    "October 1, 2025 - September 30, 2026\n"
    "Keyword\tCurrency\tAvg. monthly searches\tThree month change\tYoY change\tCompetition\t"
    "Competition (indexed value)\tTop of page bid (low range)\tTop of page bid (high range)\n"
    "japan golden week 2027\tTWD\t100 – 1K\t900%\t9900%\tLow\t12\t2.11\t75.60\n"
    "long weekends 2027\tTWD\t100 – 1K\t900%\t9900%\tLow\t8\t\t\n"
    "uae public holidays 2027\tTWD\t--\t\t\t\t\t\t\n"
)
PLANNER_ZH = (
    "关键字统计信息 2026-10-25 at 22_28_46\n"
    "2025年10月1日 - 2026年9月30日\n"
    "关键字\t货币\t平均每月搜索量\t三个月变化\t同比变化\t竞争\t竞争（索引值）\t"
    "页首出价（低位区间）\t页首出价（高位区间）\n"
    "日本黃金週\tTWD\t1万 – 10万\t0%\t0%\t低\t\t0.42\t4.34\n"
    "日本機票\tTWD\t10000 – 100000\t0%\t0%\t高\t\t3.69\t18.54\n"
)
FX = {"TWD": 0.0307}


def _write(tmp_path, text, encoding, name="kw.csv"):
    p = tmp_path / name
    p.write_bytes(text.encode(encoding))
    return p


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "cp950"])
def test_our_format_in_any_common_encoding(tmp_path, encoding):
    kws = load_keywords_csv(_write(tmp_path, OURS, encoding))
    assert [(k.term, k.volume, k.market) for k in kws] == [("日本黃金週", 30000, "tw")]


def test_our_format_saved_by_excel_as_unicode_text_is_tab_separated(tmp_path):
    kws = load_keywords_csv(_write(tmp_path, OURS.replace(",", "\t"), "utf-16"))
    assert kws[0].term == "日本黃金週"


def test_keyword_planner_export_english_ui(tmp_path):
    kws = load_keywords_csv(_write(tmp_path, PLANNER_EN, "utf-16"), fx_to_usd=FX)
    by = {k.term: k for k in kws}
    assert set(by) == {"japan golden week 2027", "long weekends 2027"}   # 沒有搜尋量（--）的列略過
    gw = by["japan golden week 2027"]
    assert gw.volume == 316                                    # 100–1K 取幾何中間值
    assert gw.cpc == pytest.approx((2.11 + 75.60) / 2 * 0.0307, abs=1e-4)   # 台幣出價換成美元
    assert gw.difficulty == 12                                 # 用競爭指數
    assert gw.market == "us"                                   # 英文關鍵字 → 美金市場
    assert by["long weekends 2027"].cpc == 0


def test_keyword_planner_export_chinese_ui(tmp_path):
    kws = load_keywords_csv(_write(tmp_path, PLANNER_ZH, "utf-16"), fx_to_usd=FX)
    by = {k.term: k for k in kws}
    assert by["日本黃金週"].volume == by["日本機票"].volume == 31623
    assert by["日本黃金週"].market == "tw"                      # 中文關鍵字 → 台幣市場
    assert (by["日本黃金週"].difficulty, by["日本機票"].difficulty) == (20, 85)   # 沒有指數時用 低／高


def test_keyword_planner_market_can_be_forced(tmp_path):
    kws = load_keywords_csv(_write(tmp_path, PLANNER_EN, "utf-16"), fx_to_usd=FX, market="tw")
    assert {k.market for k in kws} == {"tw"}


def test_keyword_planner_non_usd_bids_need_exchange_rate(tmp_path):
    with pytest.raises(ValueError, match="fx_to_usd"):
        load_keywords_csv(_write(tmp_path, PLANNER_ZH, "utf-16"))


def test_unknown_columns_give_a_readable_error(tmp_path):
    with pytest.raises(ValueError, match="找不到關鍵字欄位"):
        load_keywords_csv(_write(tmp_path, "foo,bar\n1,2\n", "utf-8"))


@pytest.mark.parametrize("raw, expected", [
    ("10 – 100", 32), ("100 – 1K", 316), ("1K – 10K", 3162), ("1万 – 10万", 31623),
    ("1000 - 10000", 3162), ("2,400", 2400), ("880", 880),
])
def test_parse_volume(raw, expected):
    assert parse_volume(raw) == expected


@pytest.mark.parametrize("raw", ["", "--", "—", "-"])
def test_parse_volume_empty(raw):
    assert parse_volume(raw) is None


def test_site_fx_reads_site_yaml(tmp_path):
    from seoengine.keywords import site_fx
    (tmp_path / "site.yaml").write_text("google:\n  fx_to_usd: {TWD: 0.0307}\n", encoding="utf-8")
    assert site_fx(tmp_path) == {"TWD": 0.0307}
    assert site_fx(tmp_path / "missing") == {}


def test_dashboard_reads_planner_export_with_site_exchange_rate(tmp_path):
    import shutil
    from pathlib import Path

    from seoengine.viz import build_dashboard_data
    project = tmp_path / "site"
    shutil.copytree(Path(__file__).parents[2] / "sites" / "holiday-calendar", project,
                    ignore=shutil.ignore_patterns("public", "dashboard", "keywords.csv", "secrets"))
    text = (project / "site.yaml").read_text(encoding="utf-8")
    (project / "site.yaml").write_text(text.replace("fx_to_usd: {}", "fx_to_usd: {TWD: 0.0307}"), encoding="utf-8")
    export = _write(project, PLANNER_ZH, "utf-16", name="Keyword Stats.csv")
    data = build_dashboard_data(project, export)
    assert {r["term"] for r in data["revenue"]["keywords"]} == {"日本黃金週", "日本機票"}


def test_cli_keywords_accepts_fx_option(tmp_path, capsys):
    from seoengine.cli import main
    export = _write(tmp_path, PLANNER_ZH, "utf-16")
    assert main(["keywords", str(export), "--fx", "TWD=0.0307"]) == 0
    assert "日本黃金週" in capsys.readouterr().out
    assert main(["forecast", str(export), "--fx", "TWD=0.0307"]) == 0


def test_cli_keywords_explains_missing_exchange_rate(tmp_path, capsys):
    from seoengine.cli import main
    assert main(["keywords", str(_write(tmp_path, PLANNER_ZH, "utf-16"))]) != 0
    assert "fx_to_usd" in capsys.readouterr().err
