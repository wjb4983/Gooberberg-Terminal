from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.domain.run_metadata_governance import missing_required_metadata
from app.schemas.jobs import JobLifecycleUpdateRequest

logger = logging.getLogger(__name__)
_SHA_RE = re.compile(r"^(sha256:)?[a-fA-F0-9]{16,128}$")


@dataclass(frozen=True, slots=True)
class GateFailure:
    category: str
    reason: str
    remediation: str


def evaluate_success_gate(*, run_type: str, run_row: Any, event_update: JobLifecycleUpdateRequest) -> GateFailure | None:
    lineage = event_update.lineage if isinstance(event_update.lineage, dict) else {}
    required_lineage = ("lineage_id", "dataset_fingerprint", "code_hash", "config_digest")
    missing_lineage = [key for key in required_lineage if not lineage.get(key)]
    if missing_lineage:
        return GateFailure(
            category="lineage_missing",
            reason=f"missing lineage fields: {', '.join(missing_lineage)}",
            remediation="Include complete lineage payload from the worker completion event.",
        )

    for key, row_attr in (("dataset_fingerprint", "dataset_fingerprint"), ("code_hash", "code_hash"), ("config_digest", "config_digest")):
        row_value = getattr(run_row, row_attr, None)
        incoming_value = lineage.get(key)
        if row_value and incoming_value and str(row_value) != str(incoming_value):
            return GateFailure(
                category="lineage_inconsistent",
                reason=f"lineage field '{key}' does not match persisted run metadata",
                remediation="Regenerate lineage from the same immutable inputs used when scheduling the run.",
            )

    policy = event_update.mismatch_policy.lower()
    expected_runtime = dict(event_update.expected_runtime or {})
    observed_runtime = dict(event_update.runtime_observed or {})
    mismatches = [key for key, value in expected_runtime.items() if key in observed_runtime and observed_runtime.get(key) != value]
    if mismatches and policy not in {"allow", "warn"}:
        return GateFailure(
            category="runtime_mismatch",
            reason=f"runtime value mismatch for keys: {', '.join(mismatches)}",
            remediation="Either align runtime-observed values with expectations or publish mismatch_policy=allow/warn.",
        )

    manifest = list(event_update.artifact_manifest or [])

    run_metadata = {}
    parameters = getattr(run_row, "parameters", None)
    if isinstance(parameters, dict):
        run_metadata_candidate = parameters.get("run_metadata")
        if isinstance(run_metadata_candidate, dict):
            run_metadata = run_metadata_candidate

    final_candidate_roles = [
        item for item in manifest if isinstance(item, dict) and str(item.get("promotion_status", "")).lower() == "final_candidate"
    ]
    if final_candidate_roles:
        missing_metadata = missing_required_metadata(run_metadata)
        if missing_metadata:
            return GateFailure(
                category="final_candidate_metadata_missing",
                reason=f"cannot label final_candidate without required run_metadata fields: {', '.join(missing_metadata)}",
                remediation="Populate run_metadata with the governance-required metadata fields before final candidate promotion.",
            )
    mandatory_roles = {
        "training": {"trained_model", "training_metrics", "run_metadata"},
        "backtest": {"backtest_metrics", "trade_log", "run_metadata"},
    }.get(run_type, set())
    role_to_entry = {str(item.get("role")): item for item in manifest if isinstance(item, dict)}
    missing_roles = sorted(role for role in mandatory_roles if role not in role_to_entry)
    if missing_roles:
        return GateFailure(
            category="artifact_manifest_missing",
            reason=f"missing mandatory artifact roles: {', '.join(missing_roles)}",
            remediation="Publish a complete artifact_manifest with every mandatory artifact role.",
        )

    for role in mandatory_roles:
        entry = role_to_entry[role]
        checksum = str(entry.get("sha256") or entry.get("checksum") or "")
        size_bytes = entry.get("size_bytes")
        if not _SHA_RE.match(checksum):
            return GateFailure(
                category="artifact_hash_invalid",
                reason=f"artifact '{role}' checksum/hash is missing or malformed",
                remediation="Populate each mandatory manifest item with a valid sha256 hash.",
            )
        if not isinstance(size_bytes, int) or size_bytes <= 0:
            return GateFailure(
                category="artifact_size_invalid",
                reason=f"artifact '{role}' size_bytes must be a positive integer",
                remediation="Ensure artifact sizes are recorded after upload and are greater than zero.",
            )

    seed = lineage.get("seed")
    metadata_seed = run_metadata.get("seed")
    persisted_seed = getattr(run_row, "seed", None)
    if persisted_seed is None and hasattr(run_row, "random_seed"):
        persisted_seed = getattr(run_row, "random_seed", None)
    if seed is None or metadata_seed is None or persisted_seed is None:
        return GateFailure(
            category="seed_missing",
            reason="seed must be present in lineage payload, persisted run row, and run metadata",
            remediation="Propagate the deterministic seed through scheduling payload, run row seed column, and run_metadata.seed.",
        )
    if not (int(seed) == int(metadata_seed) == int(persisted_seed)):
        return GateFailure(
            category="seed_inconsistent",
            reason="seed values do not match across lineage payload, run metadata, and persisted run row",
            remediation="Use a single seed source of truth and copy it to all required locations.",
        )
    return None


def emit_gate_failure_metric(*, category: str, run_type: str) -> None:
    logger.warning("success gate failure", extra={"metric": "run_success_gate_failure_total", "category": category, "run_type": run_type})
