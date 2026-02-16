from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Callable

from .errors import CollectionConnectorError, SSHConnectorError
from .parsers import (
    parse_df_p,
    parse_ipv4_from_ip_addr,
    parse_meminfo,
    parse_os_release,
    parse_uptime_seconds,
)
from .ssh_client import SSHClient

LogFn = Callable[[str, str], None]


@dataclass
class HostFacts:
    hostname: str | None = None
    fqdn: str | None = None
    machine_id: str | None = None
    ipv4: list[str] = field(default_factory=list)

    os_pretty: str | None = None
    os_id: str | None = None
    os_version_id: str | None = None
    kernel_release: str | None = None

    cpu_cores: int | None = None
    mem_total_kb: int | None = None
    uptime_sec: int | None = None

    filesystems: list[dict[str, object]] = field(default_factory=list)


def collect_host_facts(ssh: SSHClient, strict: bool, log: LogFn) -> HostFacts:
    facts = HostFacts()

    facts.hostname = _run_text(ssh, "hostname", strict, log)
    facts.fqdn = _run_text(ssh, "hostname -f", strict, log) or facts.hostname
    facts.machine_id = _run_text(ssh, "cat /etc/machine-id", strict, log)

    ip_addr_json = _run_text(ssh, "ip -j addr", strict, log)
    if ip_addr_json:
        try:
            facts.ipv4 = parse_ipv4_from_ip_addr(ip_addr_json)
        except Exception as exc:  # noqa: BLE001
            _handle_error(strict, log, f"failed to parse ip -j addr output: {exc}")
    if not facts.ipv4:
        hostname_i = _run_text(ssh, "hostname -I", strict, log)
        if hostname_i:
            facts.ipv4 = _extract_ipv4_tokens(hostname_i)

    os_release_raw = _run_text(ssh, "cat /etc/os-release", strict, log)
    if os_release_raw:
        try:
            os_values = parse_os_release(os_release_raw)
            facts.os_pretty = os_values.get("os_pretty")
            facts.os_id = os_values.get("os_id")
            facts.os_version_id = os_values.get("os_version_id")
        except Exception as exc:  # noqa: BLE001
            _handle_error(strict, log, f"failed to parse /etc/os-release: {exc}")

    facts.kernel_release = _run_text(ssh, "uname -r", strict, log)

    cpu_raw = _run_text(ssh, "nproc", strict, log)
    if cpu_raw:
        try:
            facts.cpu_cores = int(cpu_raw)
        except ValueError as exc:
            _handle_error(strict, log, f"failed to parse nproc output: {exc}")

    meminfo_raw = _run_text(ssh, "cat /proc/meminfo", strict, log)
    if meminfo_raw:
        try:
            facts.mem_total_kb = parse_meminfo(meminfo_raw)
        except Exception as exc:  # noqa: BLE001
            _handle_error(strict, log, f"failed to parse /proc/meminfo: {exc}")

    uptime_raw = _run_text(ssh, "cat /proc/uptime", strict, log)
    if uptime_raw:
        try:
            facts.uptime_sec = parse_uptime_seconds(uptime_raw)
        except Exception as exc:  # noqa: BLE001
            _handle_error(strict, log, f"failed to parse /proc/uptime: {exc}")

    df_raw = _run_text(ssh, "df -P", strict, log)
    if df_raw:
        try:
            facts.filesystems = parse_df_p(df_raw)
        except Exception as exc:  # noqa: BLE001
            _handle_error(strict, log, f"failed to parse df -P output: {exc}")

    return facts


def _run_text(ssh: SSHClient, command: str, strict: bool, log: LogFn) -> str | None:
    try:
        result = ssh.run(command)
    except SSHConnectorError as exc:
        _handle_error(strict, log, f"{command} failed: {exc}")
        return None

    if result.exit_code != 0:
        message = f"{command} returned exit={result.exit_code} stderr={result.stderr[:200]}"
        _handle_error(strict, log, message)
        return None

    return result.stdout.strip() if result.stdout else None


def _handle_error(strict: bool, log: LogFn, message: str) -> None:
    if strict:
        raise CollectionConnectorError(message)
    log("warn", message)


def _extract_ipv4_tokens(raw: str) -> list[str]:
    ipv4: list[str] = []
    for token in raw.split():
        try:
            value = str(ipaddress.ip_address(token))
        except ValueError:
            continue
        if "." in value and value not in ipv4:
            ipv4.append(value)
    return ipv4
