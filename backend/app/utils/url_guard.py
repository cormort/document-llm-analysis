"""對外 URL 的安全檢查（SSRF 防護）。

`local_url`、MCP server URL 等欄位由使用者提供，會被拿去發 HTTP 請求。
不加限制的話可以拿伺服器當跳板打內網、讀取雲端 metadata
（`http://169.254.169.254/...`）。

設計取捨：這個產品的正常用法就是連本機的 Ollama / LM Studio
（`http://localhost:11434/v1`），所以私有位址**預設允許**，
但可透過 `ALLOW_PRIVATE_LLM_URLS=false` 關閉；
link-local 與雲端 metadata 位址則**永遠禁止**。
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}

# 永遠禁止：雲端 metadata 與 link-local
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "instance-data",
}
BLOCKED_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS & GCP metadata
    ipaddress.ip_network("fd00:ec2::254/128"),
)


class UnsafeUrlError(ValueError):
    """URL 未通過安全檢查。"""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(ip in net for net in BLOCKED_NETWORKS)


def validate_outbound_url(
    url: str | None,
    *,
    allow_private: bool = True,
    field_name: str = "url",
) -> str:
    """檢查使用者提供的 URL 是否可以安全地發送請求。

    Args:
        url: 待檢查的 URL
        allow_private: 是否允許 loopback／私有網段（本機 LLM 需要）
        field_name: 錯誤訊息中顯示的欄位名稱

    Returns:
        正規化（去除結尾斜線）的 URL

    Raises:
        UnsafeUrlError: URL 空白、scheme 不合法、指向 metadata/link-local，
            或在 `allow_private=False` 時指向私有網段。
    """
    if not url or not str(url).strip():
        raise UnsafeUrlError(f"{field_name} 不可為空")

    raw = str(url).strip()
    parts = urlsplit(raw)

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(
            f"{field_name} 只允許 http/https（收到: {parts.scheme or '無 scheme'}）"
        )
    if not parts.hostname:
        raise UnsafeUrlError(f"{field_name} 缺少主機名稱")

    hostname = parts.hostname.lower().strip("[]")
    if hostname in BLOCKED_HOSTNAMES:
        raise UnsafeUrlError(f"{field_name} 指向雲端 metadata 位址，已拒絕")

    try:
        ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None = ipaddress.ip_address(
            hostname
        )
    except ValueError:
        # 域名（例如 host.docker.internal）→ 只能做字串層級檢查
        ip = None

    if ip is not None:
        if _is_blocked_ip(ip):
            raise UnsafeUrlError(f"{field_name} 指向 link-local/metadata 位址，已拒絕")
        if not allow_private and (ip.is_private or ip.is_loopback or ip.is_reserved):
            raise UnsafeUrlError(f"{field_name} 指向私有位址，已拒絕")

    return raw.rstrip("/")
