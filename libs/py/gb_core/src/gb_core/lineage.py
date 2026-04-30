"""Versioned lineage contract shared across API and workers."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_GIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
_MEDIA_TYPE_RE = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")
_ROLE_RE = re.compile(r"^[a-z0-9_./:-]{1,64}$")
_PATH_RE = re.compile(r"^[ -~]{1,2048}$")


class SourceMetadata(BaseModel):
    source_uri: str | None = Field(default=None, max_length=2048)
    source_version: str | None = Field(default=None, max_length=128)


class DatasetFingerprint(BaseModel):
    algorithm: Literal["sha256"] = "sha256"
    hash: str = Field(min_length=64, max_length=64)
    source_metadata: SourceMetadata | None = None

    @field_validator("hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("dataset_fingerprint.hash must be a lowercase sha256 hex digest")
        return value


class CodeHash(BaseModel):
    git_commit_sha: str = Field(min_length=40, max_length=40)
    dirty: bool

    @field_validator("git_commit_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if not _GIT_SHA_RE.fullmatch(value):
            raise ValueError("code_hash.git_commit_sha must be a lowercase 40-char git sha")
        return value


class ConfigDigest(BaseModel):
    algorithm: Literal["sha256"] = "sha256"
    digest: str = Field(min_length=64, max_length=64)
    canonicalization: str = Field(default="json-c14n/v1", min_length=1, max_length=64)

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("config_digest.digest must be a lowercase sha256 hex digest")
        return value


class ArtifactRecord(BaseModel):
    uri: str = Field(min_length=1, max_length=2048)
    size_bytes: int = Field(ge=0)
    algorithm: Literal["sha256"] = "sha256"
    hash: str = Field(min_length=64, max_length=64)
    media_type: str = Field(min_length=3, max_length=255)
    role: str = Field(min_length=1, max_length=64)

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        if not _PATH_RE.fullmatch(value):
            raise ValueError("artifact uri/path contains invalid characters")
        return value

    @field_validator("hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _HASH_RE.fullmatch(value):
            raise ValueError("artifact hash must be a lowercase sha256 hex digest")
        return value

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE_RE.fullmatch(value.lower()):
            raise ValueError("artifact media_type must match type/subtype")
        return value.lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if not _ROLE_RE.fullmatch(value):
            raise ValueError("artifact role must match [a-z0-9_./:-]{1,64}")
        return value


class LineageSpec(BaseModel):
    """Schema v1 evolution policy: additive optional fields only; no semantic changes."""

    lineage_version: Literal[1]
    dataset_fingerprint: DatasetFingerprint
    code_hash: CodeHash
    config_digest: ConfigDigest
    seed: int
    artifact_manifest: list[ArtifactRecord] = Field(min_length=1)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_unique_artifact_uris(self) -> "LineageSpec":
        uris = [item.uri for item in self.artifact_manifest]
        if len(uris) != len(set(uris)):
            raise ValueError("artifact_manifest entries must have unique uri/path values")
        return self


class LineageReference(BaseModel):
    dataset_fingerprint_hash: str = Field(min_length=64, max_length=64)
    code_git_commit_sha: str = Field(min_length=40, max_length=40)
    code_dirty: bool = False
    seed: int


def canonicalize_config(config: dict[str, Any]) -> str:
    """Stable JSON canonicalization used for config hashing across API/workers."""
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def resolve_lineage_spec(
    *,
    lineage: LineageSpec | None,
    lineage_ref: LineageReference | None,
    config_payload: dict[str, Any],
) -> LineageSpec:
    if lineage is not None:
        return lineage
    if lineage_ref is None:
        raise ValueError("either lineage or lineage_ref must be provided")
    canonical = canonicalize_config(config_payload)
    return LineageSpec(
        lineage_version=1,
        dataset_fingerprint={"hash": lineage_ref.dataset_fingerprint_hash},
        code_hash={"git_commit_sha": lineage_ref.code_git_commit_sha, "dirty": lineage_ref.code_dirty},
        config_digest={"digest": sha256(canonical.encode("utf-8")).hexdigest()},
        seed=lineage_ref.seed,
        artifact_manifest=[{"uri": "pending://artifacts", "size_bytes": 0, "hash": "0" * 64, "media_type": "application/json", "role": "placeholder"}],
    )
