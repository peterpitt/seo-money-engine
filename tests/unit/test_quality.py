from helpers import article_md
from seoengine.content import parse_article
from seoengine.quality import QualityConfig, check_article

CFG = QualityConfig(min_words=120)


def _article(**kw):
    return parse_article(article_md("t", kw.pop("keyword", "磨豆機推薦"), **kw))


def rules(report, severity):
    return {i.rule for i in report.issues if i.severity == severity}


def test_clean_zh_and_en_articles_have_no_issues():
    for a in (_article(), _article(keyword="best coffee grinder", lang="en")):
        report = check_article(a, config=CFG)
        assert report.issues == [], report.issues
        assert report.score == 100


def test_english_filler_detected_case_insensitive():
    a = _article(keyword="best coffee grinder", lang="en", extra="Let's Delve Into the details.")
    assert "ai-filler" in rules(check_article(a, config=CFG), "error")


def test_h1_in_body_is_error():
    a = _article(extra="# Another title")
    assert "single-h1" in rules(check_article(a, config=CFG), "error")


def test_missing_description_is_error():
    a = _article()
    a.description = ""
    assert "meta-description" in rules(check_article(a, config=CFG), "error")


def test_description_too_long_is_warning():
    a = _article()
    a.description = "很長" * 100
    assert "meta-description" in rules(check_article(a, config=CFG), "warning")


def test_title_too_long_is_warning():
    a = _article()
    a.title = "磨豆機推薦" + "超長標題" * 20
    assert "title-length" in rules(check_article(a, config=CFG), "warning")


def test_keyword_in_title_requires_all_parts():
    a = _article(keyword="手沖 磨豆機")
    a.title = "磨豆機的選購"
    assert "keyword-in-title" in rules(check_article(a, config=CFG), "error")
    a.title = "手沖用的磨豆機選購"
    assert "keyword-in-title" not in rules(check_article(a, config=CFG), "error")


def test_keyword_missing_from_intro_is_warning():
    a = _article()
    a.body_md = a.body_md.replace("磨豆機推薦之前", "開始之前", 1)
    assert "keyword-in-intro" in rules(check_article(a, config=CFG), "warning")


def test_too_few_h2_is_warning():
    a = _article()
    a.body_md = a.body_md.replace("## 實際使用心得", "實際使用心得")
    assert "h2-structure" in rules(check_article(a, config=CFG), "warning")


def test_shortcodes_and_tables_are_not_long_paragraphs():
    table = "| " + " | ".join(["欄位很長的內容"] * 20) + " |\n|" + "---|" * 20
    a = _article(extra=table + "\n\n[[compare:a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z]]")
    assert "long-paragraph" not in rules(check_article(a, config=CFG), "warning")


def test_score_floor_is_zero():
    a = _article(extra="在這個日新月異的時代 ![](a.png) ![](b.png) ![](c.png) ![](d.png) ![](e.png) ![](f.png) ![](g.png)")
    a.title = "無關"
    assert check_article(a, config=CFG).score == 0
