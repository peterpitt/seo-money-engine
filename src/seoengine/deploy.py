"""部署前端網站到 Cloudflare Pages（wrangler）。

只上傳建置好的 public/ 資料夾；收益儀表板（dashboard/）、金鑰（secrets/）、關鍵字與機會資料都在專案資料夾，
不在 public/ 裡，所以不會被傳出去。部署前會先重新建置並做安全檢查。
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import yaml

from .domains import LINK_TO_PLACEHOLDER, is_placeholder_host, is_placeholder_url
from .site import BuildError, SiteConfig, build_site


class DeployError(RuntimeError):
    pass


_PRIVATE = re.compile(r"(^|/)(dashboard|secrets)(/|$)|google-ads\.ya?ml$|keywords.*\.csv$|opportunities\.json$|\.env$")


def _project_name(project: Path) -> str:
    data = yaml.safe_load((project / "site.yaml").read_text(encoding="utf-8")) or {}
    name = str((data.get("deploy") or {}).get("cloudflare_project") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,57}", name):
        raise DeployError("請在 site.yaml 設定 deploy.cloudflare_project（小寫英數與連字號，例如 asusu-calendar）")
    return name


def check_public(folder: Path) -> None:
    leaked = [str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()
              and _PRIVATE.search(p.relative_to(folder).as_posix())]
    if leaked:
        raise DeployError(f"public 資料夾裡有不應公開的檔案，已停止部署：{', '.join(leaked[:5])}")
    placeholder_links = []
    for page in folder.rglob("*.html"):
        for host in LINK_TO_PLACEHOLDER.findall(page.read_text(encoding="utf-8", errors="ignore")):
            if is_placeholder_host(host):
                placeholder_links.append(f"{page.relative_to(folder).as_posix()} → {host}")
    if placeholder_links:
        raise DeployError("網頁裡還有連到範例網址的連結（例如 offers.yaml 的示範聯盟商品），已停止部署：" +
                          "、".join(placeholder_links[:5]))


def deploy_site(project_dir: str | Path, runner: Callable[[list[str]], int] | None = None, build: bool = True) -> Path:
    project = Path(project_dir)
    cfg = SiteConfig.load(project / "site.yaml")
    # 保留給文件與測試的網域（RFC 2606／6761）一律不能部署：example.com／org／net 與 .example .test .invalid .localhost
    if is_placeholder_url(cfg.base_url):
        raise DeployError(f"site.yaml 的 base_url 還是 {cfg.base_url}，請改成你的網域再部署（例如 https://<你的網域> 或 https://music.<你的網域>）")
    if not cfg.base_url.startswith("https://"):
        raise DeployError("base_url 必須是 https:// 開頭")
    name = _project_name(project)
    try:
        out = build_site(project).out_dir if build else project / cfg.out_dir
    except BuildError as exc:
        raise DeployError(f"建置失敗：{exc}") from exc
    check_public(out)
    # Windows 的 npx 是 npx.cmd：先用 PATH 找出完整路徑，否則 subprocess 會找不到檔案
    npx = shutil.which("npx")
    if not npx:
        raise DeployError(_NO_NODE)
    cmd = [npx, "wrangler", "pages", "deploy", str(out), "--project-name", name, "--branch", "main"]
    run = runner or (lambda c: subprocess.call(c, shell=False))
    try:
        code = run(cmd)
    except OSError as exc:
        raise DeployError(f"{_NO_NODE}（{exc}）") from exc
    if code != 0:
        raise DeployError("wrangler 部署失敗。第一次使用請先執行 npx wrangler login 登入 Cloudflare。")
    return out


_NO_NODE = "找不到 npx。請安裝 Node.js LTS（nodejs.org），安裝後關掉再重開 PowerShell，用 node -v 確認後再部署"
