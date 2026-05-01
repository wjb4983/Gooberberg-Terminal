from __future__ import annotations

from app.domain.run_metadata_governance import (
    can_label_final_candidate,
    missing_required_metadata,
    run_metadata_template,
    weekly_audit_sample,
)


def test_template_contains_required_fields() -> None:
    template = run_metadata_template()
    assert set(template) == {
        "hypothesis_id",
        "dataset_snapshot_id",
        "code_commit_hash",
        "parameter_set_id",
        "random_seed",
        "cost_model_version",
    }


def test_missing_required_metadata_detects_missing_values() -> None:
    missing = missing_required_metadata({"hypothesis_id": "hyp-1", "random_seed": 9})
    assert set(missing) == {"dataset_snapshot_id", "code_commit_hash", "parameter_set_id", "cost_model_version"}


def test_can_label_final_candidate_only_when_complete() -> None:
    assert not can_label_final_candidate({"hypothesis_id": "hyp-1"})
    assert can_label_final_candidate(
        {
            "hypothesis_id": "hyp-1",
            "dataset_snapshot_id": "ds-1",
            "code_commit_hash": "abc123",
            "parameter_set_id": "ps-1",
            "random_seed": 11,
            "cost_model_version": "v3",
        }
    )


def test_weekly_audit_samples_five_runs_deterministically() -> None:
    run_ids = [f"run-{idx}" for idx in range(10)]
    sample = weekly_audit_sample(run_ids, seed=42)
    assert len(sample) == 5
    assert sample == weekly_audit_sample(run_ids, seed=42)
