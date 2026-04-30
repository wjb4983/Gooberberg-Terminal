from pydantic import ValidationError

from gb_core.lineage import LineageSpec


def _valid_lineage() -> dict:
    return {
        "lineage_version": 1,
        "dataset_fingerprint": {"algorithm": "sha256", "hash": "a" * 64},
        "code_hash": {"git_commit_sha": "b" * 40, "dirty": False},
        "config_digest": {"algorithm": "sha256", "digest": "c" * 64, "canonicalization": "json-c14n/v1"},
        "seed": 42,
        "artifact_manifest": [
            {
                "uri": "file:///artifacts/model.bin",
                "size_bytes": 123,
                "algorithm": "sha256",
                "hash": "d" * 64,
                "media_type": "application/octet-stream",
                "role": "model",
            }
        ],
    }


def test_lineage_spec_accepts_valid_payload() -> None:
    spec = LineageSpec.model_validate(_valid_lineage())
    assert spec.lineage_version == 1


def test_lineage_spec_rejects_invalid_hash() -> None:
    payload = _valid_lineage()
    payload["dataset_fingerprint"]["hash"] = "XYZ"
    try:
        LineageSpec.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("expected ValidationError")
