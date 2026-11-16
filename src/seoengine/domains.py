"""保留給範例與測試的網域（RFC 2606／6761）：這些網址不能出現在正式網站上。"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

_PLACEHOLDER = re.compile(r"(^|\.)example\.(com|org|net)$|\.(example|test|invalid|localhost)$|^localhost$")


def is_placeholder_host(host: str) -> bool:
    return bool(_PLACEHOLDER.search((host or "").lower().rstrip(".")))


def is_placeholder_url(url: str) -> bool:
    return is_placeholder_host(urlsplit(url).hostname or "")


# 網頁裡指向範例網域的連結（href／src／meta refresh 的 url=），純文字不算
LINK_TO_PLACEHOLDER = re.compile(
    r"""(?:href|src|content)\s*=\s*["'][^"']*?(?:url=)?https?://([^/"'\s:?#]+)""", re.I)
