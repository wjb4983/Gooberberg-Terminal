#!/usr/bin/env python3
"""Validate training model metadata, adapter registry parity, and contract-test coverage."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SRC = REPO_ROOT / "services" / "worker-training" / "src"
DEFAULT_TESTS_DIR = REPO_ROOT / "services" / "worker-training" / "tests"


def _load_training_runtime(training_src: Path):
    sys.path.insert(0, str(training_src))
    from worker_training.adapters.phase1 import PHASE1_MODEL_METADATA
    from worker_training.adapters.phase2 import PHASE2_MODEL_METADATA
    from worker_training.adapters.phase3 import PHASE3_MODEL_METADATA
    from worker_training.main import ADAPTERS

    metadata = [*PHASE1_MODEL_METADATA, *PHASE2_MODEL_METADATA, *PHASE3_MODEL_METADATA]
    return metadata, ADAPTERS


def _collect_contract_test_functions(tests_dir: Path) -> set[str]:
    functions: set[str] = set()
    for path in sorted(tests_dir.rglob("test_*.py")):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                functions.add(node.name)
    return functions


def check_consistency(metadata: list[object], adapters: dict[str, object], test_functions: set[str]) -> list[str]:
    errors: list[str] = []

    for row in metadata:
        if not getattr(row, "implemented", False):
            continue

        model_id = str(getattr(row, "model_name"))
        adapter = adapters.get(model_id)
        if adapter is None:
            errors.append(f"missing adapter: model_id='{model_id}'")
            continue

        capabilities = tuple(getattr(row, "capabilities", ()))
        if not capabilities:
            errors.append(f"missing task/subtask declarations: model_id='{model_id}'")
        else:
            has_missing_task_subtask = any(
                not getattr(capability, "task", "") or not getattr(capability, "subtask", "") for capability in capabilities
            )
            if has_missing_task_subtask:
                errors.append(f"missing task/subtask declarations: model_id='{model_id}'")

        expected_contract_test = "test_adapter_contract_suite_and_matrix_output"
        if expected_contract_test not in test_functions:
            errors.append(
                "missing contract-test coverage: "
                f"model_id='{model_id}', expected_test='{expected_contract_test}'"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-src", type=Path, default=DEFAULT_TRAINING_SRC)
    parser.add_argument("--tests-dir", type=Path, default=DEFAULT_TESTS_DIR)
    args = parser.parse_args()

    metadata, adapters = _load_training_runtime(args.training_src)
    test_functions = _collect_contract_test_functions(args.tests_dir)
    errors = check_consistency(metadata=metadata, adapters=adapters, test_functions=test_functions)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    implemented = sum(1 for row in metadata if getattr(row, "implemented", False))
    print(f"OK: training metadata consistency passed (implemented={implemented}, adapters={len(adapters)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
