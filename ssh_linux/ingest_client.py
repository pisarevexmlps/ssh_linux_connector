from __future__ import annotations

import requests

from .errors import IngestConnectorError


def post_batch(
    ingest_url: str,
    ingest_token: str,
    task_id: str,
    batch_payload: dict,
    timeout_sec: int,
) -> str:
    url = f"{ingest_url.rstrip('/')}/v1/ingest/batches"
    headers = {
        "Authorization": f"Bearer {ingest_token}",
        "Idempotency-Key": task_id,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=batch_payload, headers=headers, timeout=timeout_sec)
    except requests.RequestException as exc:
        raise IngestConnectorError(f"ingest request failed: {exc}") from exc

    if response.status_code not in (200, 201):
        body = response.text.strip().replace("\n", " ")
        raise IngestConnectorError(
            f"ingest failed status={response.status_code} body={body[:500]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise IngestConnectorError("ingest response is not valid JSON") from exc

    batch_id = _extract_batch_id(payload)
    if not batch_id:
        raise IngestConnectorError("ingest response JSON missing batch_id")

    return batch_id


def _extract_batch_id(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None

    direct_keys = ["batch_id", "batchId", "id"]
    for key in direct_keys:
        value = payload.get(key)
        if value:
            return str(value)

    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in direct_keys:
            value = nested.get(key)
            if value:
                return str(value)

    return None
