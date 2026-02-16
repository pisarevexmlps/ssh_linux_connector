from __future__ import annotations

from dataclasses import dataclass

import paramiko

from .errors import SSHConnectorError
from .models import Target


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class SSHClient:
    def __init__(self, target: Target, timeout_sec: int) -> None:
        self._target = target
        self._timeout_sec = timeout_sec
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict[str, object] = {
            "hostname": self._target.address,
            "port": self._target.port,
            "username": self._target.user,
            "timeout": self._timeout_sec,
            "banner_timeout": self._timeout_sec,
            "auth_timeout": self._timeout_sec,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if self._target.auth.method == "key":
            kwargs["key_filename"] = self._target.auth.key_path
        else:
            kwargs["password"] = self._target.auth.password

        try:
            client.connect(**kwargs)
        except (paramiko.AuthenticationException, paramiko.SSHException, OSError) as exc:
            raise SSHConnectorError(f"SSH connect/auth failed for {self._target.address}") from exc

        self._client = client

    def run(self, command: str, timeout_sec: int | None = None) -> CommandResult:
        if self._client is None:
            raise SSHConnectorError("SSH client is not connected")

        try:
            _, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout_sec or self._timeout_sec,
            )
            stdout_value = stdout.read().decode("utf-8", errors="replace").strip()
            stderr_value = stderr.read().decode("utf-8", errors="replace").strip()
            exit_code = stdout.channel.recv_exit_status()
            return CommandResult(exit_code=exit_code, stdout=stdout_value, stderr=stderr_value)
        except (paramiko.SSHException, OSError) as exc:
            raise SSHConnectorError(f"SSH command execution failed: {command}") from exc

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
