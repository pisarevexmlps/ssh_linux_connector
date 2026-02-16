from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    SSH_ERROR = 2
    COLLECTION_ERROR = 3
    INGEST_ERROR = 4
    VALIDATION_ERROR = 5


class ConnectorError(Exception):
    """Base connector exception with a stable exit-code mapping."""

    exit_code: ExitCode = ExitCode.COLLECTION_ERROR


class SSHConnectorError(ConnectorError):
    exit_code = ExitCode.SSH_ERROR


class CollectionConnectorError(ConnectorError):
    exit_code = ExitCode.COLLECTION_ERROR


class IngestConnectorError(ConnectorError):
    exit_code = ExitCode.INGEST_ERROR


class ValidationConnectorError(ConnectorError):
    exit_code = ExitCode.VALIDATION_ERROR


def map_exception_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, ConnectorError):
        return int(exc.exit_code)
    return int(ExitCode.COLLECTION_ERROR)
