import paramiko
import pytest

from ssh_linux.errors import SSHConnectorError
from ssh_linux.models import Target
from ssh_linux.ssh_client import SSHClient


class _FailingClient:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def set_missing_host_key_policy(self, _policy: object) -> None:
        return None

    def connect(self, **_kwargs: object) -> None:
        raise self._error


def test_connect_error_includes_target_context_and_cause_password_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = paramiko.AuthenticationException("Authentication failed")
    monkeypatch.setattr(paramiko, "SSHClient", lambda: _FailingClient(error))

    target = Target.model_validate(
        {
            "type": "host",
            "address": "10.20.30.40",
            "port": 2222,
            "user": "root",
            "auth": {"method": "password", "password": "super-secret"},
            "meta": {},
        }
    )

    with pytest.raises(SSHConnectorError) as exc_info:
        SSHClient(target=target, timeout_sec=15).connect()

    message = str(exc_info.value)
    assert "host=10.20.30.40" in message
    assert "port=2222" in message
    assert "user=root" in message
    assert "auth_method=password" in message
    assert "timeout_sec=15" in message
    assert "cause=AuthenticationException: Authentication failed" in message


def test_connect_error_includes_key_path_for_key_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    error = ConnectionRefusedError("Connection refused")
    monkeypatch.setattr(paramiko, "SSHClient", lambda: _FailingClient(error))

    target = Target.model_validate(
        {
            "type": "host",
            "address": "ssh.example.internal",
            "port": 22,
            "user": "ubuntu",
            "auth": {"method": "key", "key_path": "/home/user/.ssh/id_rsa"},
            "meta": {},
        }
    )

    with pytest.raises(SSHConnectorError) as exc_info:
        SSHClient(target=target, timeout_sec=60).connect()

    message = str(exc_info.value)
    assert "auth_method=key" in message
    assert "key_path=/home/user/.ssh/id_rsa" in message
    assert "cause=ConnectionRefusedError: Connection refused" in message
