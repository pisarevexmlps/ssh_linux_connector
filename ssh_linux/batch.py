from __future__ import annotations

from datetime import datetime, timezone

from . import __version__
from .collectors import HostFacts
from .models import BatchV1, Entity, FileSystemFact, HostAttributes, HostKeys, Target


def build_batch(
    run_id: str,
    task_id: str,
    target: Target,
    facts: HostFacts,
    schema_version: str = "1.0",
) -> dict:
    external_id = facts.fqdn or facts.hostname or target.address

    keys = HostKeys(
        hostname=facts.hostname,
        fqdn=facts.fqdn,
        machine_id=facts.machine_id,
        ipv4=facts.ipv4 or None,
    )
    attributes = HostAttributes(
        os_pretty=facts.os_pretty,
        os_id=facts.os_id,
        os_version_id=facts.os_version_id,
        kernel_release=facts.kernel_release,
        cpu_cores=facts.cpu_cores,
        mem_total_kb=facts.mem_total_kb,
        uptime_sec=facts.uptime_sec,
        filesystems=[FileSystemFact.model_validate(item) for item in facts.filesystems],
    )

    batch = BatchV1(
        schema_version=schema_version,
        source="ssh_linux",
        run_id=run_id,
        job_id=task_id,
        collected_at=_utc_now_rfc3339(),
        entities=[
            Entity(
                entity_type="host",
                external_id=external_id,
                keys=keys,
                attributes=attributes,
            )
        ],
        relations=[],
        meta={
            "target_address": target.address,
            "connector_version": __version__,
        },
    )
    return batch.model_dump(exclude_none=True)


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
