# ssh_linux_connector

A basic CMDB discovery connector named `ssh_linux`.

It connects to a Linux host over SSH, collects a small set of host facts, builds a BatchV1 payload (`schema_version=1.0`), and posts it to `cmdb-ingest-api`.

## What It Collects

- Host identity: hostname, fqdn, machine_id (optional), IPv4 addresses
- OS and kernel: `/etc/os-release` fields and `uname -r`
- CPU and memory: `nproc`, `MemTotal` from `/proc/meminfo`
- Uptime: `/proc/uptime`
- Filesystems: `df -P`

## Run Locally

```bash
python -m ssh_linux \
  --run-id 11111111-1111-1111-1111-111111111111 \
  --task-id 22222222-2222-2222-2222-222222222222 \
  --target-json '{"type":"host","address":"95.179.141.247","port":22,"user":"ubuntu","auth":{"method":"key","key_path":"/home/user/.ssh/id_rsa"},"meta":{"env":"prod","name":"myhost-01"}}' \
  --ingest-url http://cmdb-ingest-api:8080 \
  --ingest-token "$INGEST_TOKEN" \
  --schema-version 1.0 \
  --timeout-sec 120
```

On success, stdout includes:

```text
BATCH_ID=<uuid>
```

## `target-json` Format

```json
{
  "type": "host",
  "address": "10.0.0.5",
  "port": 22,
  "user": "ubuntu",
  "auth": {
    "method": "key",
    "key_path": "/path/to/key"
  },
  "meta": {
    "env": "prod",
    "name": "myhost-01"
  }
}
```

Password auth is also supported:

```json
{
  "auth": {
    "method": "password",
    "password": "***"
  }
}
```

Secrets (`ingest-token`, password) are never printed in logs.

## Idempotency and Ingest API

The connector posts to:

- `POST {ingest_url}/v1/ingest/batches`

Headers include:

- `Authorization: Bearer <ingest-token>`
- `Idempotency-Key: <task-id>`
- `Content-Type: application/json`

Re-running with the same `task-id` is idempotent by design.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Files

- `cmdb-connector.yaml` connector manifest
- `ssh_linux/` connector package
- `tests/test_parsers.py` parser tests
