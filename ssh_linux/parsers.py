from __future__ import annotations

import json
import re
from typing import Any

_OS_RELEASE_KEYS = {
    "PRETTY_NAME": "os_pretty",
    "ID": "os_id",
    "VERSION_ID": "os_version_id",
}


def parse_os_release(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] in {'"', "'"} and value[-1] == value[0]:
            value = value[1:-1]
        mapped_key = _OS_RELEASE_KEYS.get(key)
        if mapped_key:
            values[mapped_key] = value
    return values


def parse_meminfo(raw: str) -> int | None:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB$", raw, re.MULTILINE)
    if not match:
        return None
    return int(match.group(1))


def parse_df_p(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return rows
    if lines[0].lower().startswith("filesystem"):
        lines = lines[1:]

    for line in lines:
        parts = re.split(r"\s+", line, maxsplit=5)
        if len(parts) != 6:
            continue
        filesystem, size_kb, used_kb, avail_kb, _capacity, mountpoint = parts
        try:
            rows.append(
                {
                    "filesystem": filesystem,
                    "size_kb": int(size_kb),
                    "used_kb": int(used_kb),
                    "avail_kb": int(avail_kb),
                    "mountpoint": mountpoint,
                }
            )
        except ValueError:
            continue
    return rows


def parse_ipv4_from_ip_addr(raw: str) -> list[str]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    ipv4: list[str] = []
    for iface in payload:
        if iface.get("ifname") == "lo":
            continue
        for addr in iface.get("addr_info", []):
            if addr.get("family") != "inet":
                continue
            value = str(addr.get("local", "")).strip()
            if value and value not in ipv4:
                ipv4.append(value)
    return ipv4


def parse_uptime_seconds(raw: str) -> int | None:
    first = raw.strip().split(" ", 1)[0]
    if not first:
        return None
    try:
        return int(float(first))
    except ValueError:
        return None
