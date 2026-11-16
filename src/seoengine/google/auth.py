"""Google Ads API 的 OAuth 授權：開瀏覽器登入一次，取得 refresh token，寫成 google-ads.yaml。"""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


def _cid(raw: str) -> str:
    cid = re.sub(r"\D", "", raw or "")
    if raw and len(cid) != 10:
        raise ValueError(f"客戶 ID 應為 10 碼數字，收到 {raw!r}")
    return cid


def _default_flow_factory(client_secrets: Path, scopes: list[str]):
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('尚未安裝 OAuth 套件，請執行：pip install -e ".[google]"') from exc
    return InstalledAppFlow.from_client_secrets_file(str(client_secrets), scopes=scopes)


def create_ads_yaml(client_secrets: str | Path, developer_token: str | None, customer_id: str, out: str | Path,
                    login_customer_id: str = "", flow_factory=None) -> Path:
    """執行桌面版 OAuth 流程（會開瀏覽器），把憑證寫進 out，權限設為只有自己可讀。"""
    flow = (flow_factory or _default_flow_factory)(Path(client_secrets), [ADS_SCOPE])
    creds = flow.run_local_server(port=0, open_browser=True)
    config = flow.client_config
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": creds.refresh_token,
        "use_proto_plus": True,
        "customer_id": _cid(customer_id),
    }
    if login_customer_id:
        data["login_customer_id"] = _cid(login_customer_id)
    if developer_token and developer_token.strip():
        # 2026-09-09 起 API 會忽略 developer token（權限改由 Cloud 專案控管）；有填就保留，相容舊設定
        data = {"developer_token": developer_token.strip(), **data}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    guard = out.parent / ".gitignore"
    if not guard.exists():
        guard.write_text("*\n", encoding="utf-8")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
    os.chmod(out, 0o600)
    return out
