"""CI 設定的回歸測試：自動部署到 Cloudflare Pages，金鑰只從 GitHub Secrets 讀取。"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))


def _steps(job):
    return CI["jobs"][job]["steps"]


def _runs(job):
    return " ".join(str(s.get("run", "")) for s in _steps(job))


def test_ci_tests_then_deploys_holiday_site():
    assert "pytest" in _runs("test")
    assert "sites/holiday-calendar" in CI["env"]["SITES"].split()
    deploy = CI["jobs"]["deploy"]
    assert deploy["needs"] == "test"
    assert "main" in deploy["if"]
    assert "seoengine deploy" in _runs("deploy")


def test_ci_uses_cloudflare_secrets_not_inline_tokens():
    env = CI["jobs"]["deploy"]["env"]
    assert env["CLOUDFLARE_API_TOKEN"] == "${{ secrets.CLOUDFLARE_API_TOKEN }}"
    assert env["CLOUDFLARE_ACCOUNT_ID"] == "${{ secrets.CLOUDFLARE_ACCOUNT_ID }}"


def test_ci_no_longer_publishes_to_github_pages():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "deploy-pages" not in text and "coffee-demo" not in text


def test_site_is_rebuilt_weekly_so_countdowns_and_featured_year_stay_fresh():
    triggers = CI.get("on") or CI.get(True)            # PyYAML 會把 on 讀成 True
    crons = [s["cron"] for s in triggers.get("schedule", [])]
    assert len(crons) == 1 and len(crons[0].split()) == 5
    assert "schedule" in CI["jobs"]["deploy"]["if"] or "pull_request" in CI["jobs"]["deploy"]["if"]


# ---------------------------------------------------------------- 多個網站（主網域＋子網域）
def _matrix_sites():
    return CI["jobs"]["deploy"]["strategy"]["matrix"]["site"]


def test_deploy_runs_once_per_site_from_a_matrix():
    sites = _matrix_sites()
    assert "sites/holiday-calendar" in sites
    assert "${{ matrix.site }}" in _runs("deploy")
    assert CI["jobs"]["deploy"]["strategy"].get("fail-fast") is False      # 一個網站失敗不影響其他網站


def test_every_deployed_site_has_its_own_cloudflare_project():
    names = []
    for site in _matrix_sites():
        config = yaml.safe_load((ROOT / site / "site.yaml").read_text(encoding="utf-8"))
        names.append(config["deploy"]["cloudflare_project"])
    assert len(names) == len(set(names))


def test_quality_gate_runs_for_every_deployed_site():
    gated = CI["env"]["SITES"].split()
    assert gated == _matrix_sites()
    assert "$SITES" in _runs("test")


def test_deploy_is_opt_in_so_a_fresh_repo_without_secrets_stays_green():
    """還沒設定 Cloudflare 金鑰的新 repo 不該每次 push 都部署失敗：要先把 repo 變數 AUTO_DEPLOY 設成 true 才部署。"""
    assert "vars.AUTO_DEPLOY == 'true'" in CI["jobs"]["deploy"]["if"]
