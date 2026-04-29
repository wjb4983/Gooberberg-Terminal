#!/usr/bin/env python3
"""Generate model adapter scaffolding from a model_id."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_DIR = REPO_ROOT / "services" / "service-data" / "src" / "service_data" / "market_data" / "providers"
TESTS_DIR = REPO_ROOT / "services" / "service-data" / "tests"
DOCS_DIR = REPO_ROOT / "docs" / "model-adapters"
DOCS_INDEX = DOCS_DIR / "README.md"


class GenerationError(Exception):
    pass


def _validate_model_id(model_id: str) -> None:
    if not re.fullmatch(r"[a-z0-9_]+", model_id):
        raise GenerationError("model_id must match ^[a-z0-9_]+$")


def _to_class_name(model_id: str) -> str:
    return "".join(part.capitalize() for part in model_id.split("_")) + "Adapter"


def _provider_file(model_id: str, class_name: str) -> str:
    return f'''"""{model_id} provider adapter stub."""

from __future__ import annotations

from datetime import datetime

from service_data.market_data.models import CanonicalBar, Resolution
from service_data.market_data.providers.base import MarketDataProvider, ProviderError


class {class_name}(MarketDataProvider):
    """Adapter stub for provider `{model_id}`."""

    provider_name = "{model_id}"

    def fetch_bars(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        resolution: Resolution,
    ) -> list[CanonicalBar]:
        raise ProviderError("not_implemented", "TODO: implement {model_id} adapter")
'''


def _validation_file(model_id: str, class_name: str) -> str:
    return f'''"""Validation helpers for {model_id} adapter."""

from __future__ import annotations

from service_data.market_data.providers.{model_id}_adapter import {class_name}


def validate_{model_id}_adapter_contract() -> None:
    """Smoke validation stub for adapter contract wiring."""
    adapter = {class_name}()
    assert adapter.provider_name == "{model_id}"
'''


def _test_file(model_id: str, class_name: str) -> str:
    return f'''from __future__ import annotations

from service_data.market_data.providers.{model_id}_adapter import {class_name}
from service_data.market_data.providers.{model_id}_validation import validate_{model_id}_adapter_contract


def test_{model_id}_adapter_provider_name_contract() -> None:
    adapter = {class_name}()
    assert adapter.provider_name == "{model_id}"


def test_{model_id}_validation_stub_imports_and_runs() -> None:
    validate_{model_id}_adapter_contract()
'''


def _doc_file(model_id: str, class_name: str) -> str:
    return f'''# {model_id} adapter scaffold

Generated scaffold for `{model_id}`.

## Generated components

- Adapter class: `services/service-data/src/service_data/market_data/providers/{model_id}_adapter.py` (`{class_name}`)
- Validation stub: `services/service-data/src/service_data/market_data/providers/{model_id}_validation.py`
- Unit test template: `services/service-data/tests/test_{model_id}_adapter_template.py`

## Next steps

1. Implement `fetch_bars` in `{class_name}`.
2. Expand validation checks beyond provider name.
3. Replace template assertions with contract/integration tests.
'''


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise GenerationError(f"Refusing to overwrite existing file: {path.relative_to(REPO_ROOT)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _upsert_docs_index(model_id: str) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    line = f"- [{model_id}](./{model_id}.md)"
    if not DOCS_INDEX.exists():
        DOCS_INDEX.write_text("# Model adapter scaffolds\n\n## Generated entries\n\n", encoding="utf-8")

    existing = DOCS_INDEX.read_text(encoding="utf-8")
    if line in existing:
        return
    suffix = "" if existing.endswith("\n") else "\n"
    DOCS_INDEX.write_text(f"{existing}{suffix}{line}\n", encoding="utf-8")


def generate(model_id: str) -> list[Path]:
    _validate_model_id(model_id)
    class_name = _to_class_name(model_id)

    provider_path = PROVIDERS_DIR / f"{model_id}_adapter.py"
    validation_path = PROVIDERS_DIR / f"{model_id}_validation.py"
    test_path = TESTS_DIR / f"test_{model_id}_adapter_template.py"
    doc_path = DOCS_DIR / f"{model_id}.md"

    _write_new(provider_path, _provider_file(model_id, class_name))
    _write_new(validation_path, _validation_file(model_id, class_name))
    _write_new(test_path, _test_file(model_id, class_name))
    _write_new(doc_path, _doc_file(model_id, class_name))
    _upsert_docs_index(model_id)
    return [provider_path, validation_path, test_path, doc_path, DOCS_INDEX]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_id", help="Lowercase identifier, e.g. alpha_vantage")
    args = parser.parse_args()

    try:
        files = generate(args.model_id)
    except GenerationError as exc:
        parser.error(str(exc))

    for file_path in files:
        print(file_path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
