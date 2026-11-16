from pathlib import PureWindowsPath
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from helpers import article_md, write_project
from seoengine.deploy import DeployError, deploy_site
from seoengine.site import build_site

scenarios("../../features/deploy.feature")


@given(parsers.parse('一個網站專案，網址為 "{url}"，Cloudflare Pages 專案為 "{name}"'))
def given_project(ctx, tmp_path, url, name):
    root = write_project(tmp_path / "site", base_url=url, deploy={"cloudflare_project": name})
    (root / "content" / "a.md").write_text(article_md("a", "磨豆機推薦"), encoding="utf-8")
    ctx["project"] = root


@given("專案裡有收益儀表板與 Google 金鑰")
def given_private(ctx):
    (ctx["project"] / "dashboard").mkdir()
    (ctx["project"] / "dashboard" / "index.html").write_text("revenue", encoding="utf-8")
    (ctx["project"] / "secrets").mkdir()
    (ctx["project"] / "secrets" / "google-ads.yaml").write_text("refresh_token: x", encoding="utf-8")


@given(parsers.parse('網站網址改成 "{url}"'))
def given_url(ctx, url):
    path = ctx["project"] / "site.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["site"]["base_url"] = url
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")


@when("我建置網站")
def when_build(ctx):
    ctx["out"] = build_site(ctx["project"]).out_dir


@when("我部署網站")
def when_deploy(ctx):
    calls = []

    def runner(cmd):
        calls.append(cmd)
        folder = cmd[cmd.index("deploy") + 1]
        from pathlib import Path
        ctx["uploaded"] = sorted(str(p.relative_to(folder)) for p in Path(folder).rglob("*"))
        return 0

    ctx["calls"] = calls
    try:
        deploy_site(ctx["project"], runner=runner)
    except DeployError as exc:
        ctx["error"] = exc


@then(parsers.parse('應執行 wrangler 部署 "{folder}" 資料夾到專案 "{name}"'))
def then_wrangler(ctx, folder, name):
    [cmd] = ctx["calls"]
    assert PureWindowsPath(cmd[0]).stem == "npx"                  # 完整路徑，Windows 上是 ...\npx.cmd
    assert cmd[1:4] == ["wrangler", "pages", "deploy"]
    assert cmd[4].endswith(folder) and cmd[cmd.index("--project-name") + 1] == name


@then("上傳的資料夾不應包含儀表板或金鑰")
def then_no_private(ctx):
    assert ctx["uploaded"]
    assert not any(p.startswith(("dashboard", "secrets")) or "google-ads" in p for p in ctx["uploaded"])


@then(parsers.parse('部署應被拒絕，訊息包含 "{text}"'))
def then_refused(ctx, text):
    assert "error" in ctx and text in str(ctx["error"]) and not ctx["calls"]
