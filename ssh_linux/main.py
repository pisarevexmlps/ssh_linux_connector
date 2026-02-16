from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from uuid import UUID

from .errors import ExitCode, IngestConnectorError, SSHConnectorError, ValidationConnectorError


class ConnectorArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationConnectorError(message)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = ConnectorArgumentParser(description="CMDB connector that discovers Linux hosts over SSH")
    parser.add_argument("--run-id", required=True, help="Run UUID")
    parser.add_argument("--task-id", required=True, help="Task UUID")
    parser.add_argument("--target-json", required=True, help="Target JSON string")
    parser.add_argument("--ingest-url", required=True, help="Ingest API base URL")
    parser.add_argument("--ingest-token", required=True, help="Ingest API bearer token")
    parser.add_argument("--schema-version", required=True, choices=["1.0"], help="Batch schema version")
    parser.add_argument("--timeout-sec", type=int, default=120, help="Connector timeout in seconds")
    parser.add_argument(
        "--strict",
        nargs="?",
        const="true",
        default="false",
        type=parse_bool,
        help="Strict mode for command/parse failures",
    )
    return parser.parse_args(argv)


def parse_bool(value: str) -> bool:
    true_values = {"1", "true", "yes", "y", "on"}
    false_values = {"0", "false", "no", "n", "off"}

    normalized = value.strip().lower()
    if normalized in true_values:
        return True
    if normalized in false_values:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {value}")


def log(level: str, event: str, **fields: object) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "level": level,
        "event": event,
        **fields,
    }
    print(json.dumps(payload, separators=(",", ":")), file=sys.stderr, flush=True)


def validate_uuid(value: str, field_name: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise ValidationConnectorError(f"{field_name} must be a valid UUID") from exc


def run(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    except ValidationConnectorError as exc:
        log("error", "validation_error", message=str(exc))
        return int(ExitCode.VALIDATION_ERROR)

    try:
        from pydantic import ValidationError as PydanticValidationError

        from .batch import build_batch
        from .collectors import collect_host_facts
        from .ingest_client import post_batch
        from .models import Target
        from .ssh_client import SSHClient
    except ModuleNotFoundError as exc:
        log("error", "dependency_error", message=f"missing dependency: {exc.name}")
        return int(ExitCode.VALIDATION_ERROR)

    try:
        run_id = validate_uuid(args.run_id, "run-id")
        task_id = validate_uuid(args.task_id, "task-id")
    except ValidationConnectorError as exc:
        log("error", "validation_error", message=str(exc))
        return int(ExitCode.VALIDATION_ERROR)

    try:
        target_data = json.loads(args.target_json)
    except json.JSONDecodeError:
        log("error", "validation_error", message="target-json must be valid JSON")
        return int(ExitCode.VALIDATION_ERROR)

    try:
        target = Target.model_validate(target_data)
    except PydanticValidationError:
        log("error", "validation_error", message="target-json failed schema validation")
        return int(ExitCode.VALIDATION_ERROR)

    context = {
        "run_id": run_id,
        "task_id": task_id,
        "target_address": target.address,
    }

    log("info", "connector_started", strict=args.strict, timeout_sec=args.timeout_sec, **context)

    try:
        with SSHClient(target, timeout_sec=args.timeout_sec) as ssh:
            log("info", "ssh_connected", **context)
            facts = collect_host_facts(
                ssh,
                strict=args.strict,
                log=lambda level, message: log(level, "collector_warning", message=message, **context),
            )
            log("info", "collection_complete", **context)
    except SSHConnectorError as exc:
        log("error", "ssh_error", message=str(exc), **context)
        return int(ExitCode.SSH_ERROR)
    except Exception as exc:  # noqa: BLE001
        log("error", "collection_error", message=str(exc), **context)
        return int(ExitCode.COLLECTION_ERROR)

    try:
        batch_payload = build_batch(
            run_id=run_id,
            task_id=task_id,
            target=target,
            facts=facts,
            schema_version=args.schema_version,
        )
    except Exception as exc:  # noqa: BLE001
        log("error", "batch_build_error", message=str(exc), **context)
        return int(ExitCode.COLLECTION_ERROR)

    try:
        batch_id = post_batch(
            ingest_url=args.ingest_url,
            ingest_token=args.ingest_token,
            task_id=task_id,
            batch_payload=batch_payload,
            timeout_sec=args.timeout_sec,
        )
    except IngestConnectorError as exc:
        log("error", "ingest_error", message=str(exc), **context)
        return int(ExitCode.INGEST_ERROR)

    log("info", "ingest_success", batch_id=batch_id, **context)
    print(f"BATCH_ID={batch_id}", flush=True)
    return int(ExitCode.SUCCESS)


def main() -> int:
    return run()
