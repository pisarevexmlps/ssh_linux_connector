from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetAuth(BaseModel):
    method: Literal["key", "password"]
    key_path: Optional[str] = None
    password: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_auth(self) -> "TargetAuth":
        if self.method == "key" and not self.key_path:
            raise ValueError("auth.key_path is required when auth.method=key")
        if self.method == "password" and not self.password:
            raise ValueError("auth.password is required when auth.method=password")
        return self


class Target(BaseModel):
    type: Literal["host"]
    address: str
    port: int = Field(default=22, ge=1, le=65535)
    user: str
    auth: TargetAuth
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class FileSystemFact(BaseModel):
    filesystem: str
    size_kb: int
    used_kb: int
    avail_kb: int
    mountpoint: str

    model_config = ConfigDict(extra="forbid")


class HostKeys(BaseModel):
    hostname: Optional[str] = None
    fqdn: Optional[str] = None
    machine_id: Optional[str] = None
    ipv4: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class HostAttributes(BaseModel):
    os_pretty: Optional[str] = None
    os_id: Optional[str] = None
    os_version_id: Optional[str] = None
    kernel_release: Optional[str] = None
    cpu_cores: Optional[int] = None
    mem_total_kb: Optional[int] = None
    uptime_sec: Optional[int] = None
    filesystems: list[FileSystemFact] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class Entity(BaseModel):
    entity_type: Literal["host"]
    external_id: str
    keys: HostKeys
    attributes: HostAttributes

    model_config = ConfigDict(extra="forbid")


class BatchV1(BaseModel):
    schema_version: Literal["1.0"]
    source: str
    run_id: str
    job_id: str
    collected_at: str
    entities: list[Entity]
    relations: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
