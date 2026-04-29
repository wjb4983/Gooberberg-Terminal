from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_linter_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "lint-model-catalog.py"
    spec = importlib.util.spec_from_file_location("lint_model_catalog", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_linter_reports_required_fields_and_missing_warnings(tmp_path: Path) -> None:
    module = _load_linter_module()
    fixture = tmp_path / "invalid_required.yaml"
    fixture.write_text(
        """
- id: model-1
  slug: model-1-slug
  model_family: family_1
  model_name: Model One
  description: missing warnings and references
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errors = module.lint_catalog_file(fixture)

    assert any("missing required field 'warnings'" in err for err in errors)
    assert any("missing required field 'references'" in err for err in errors)


def test_linter_reports_duplicate_ids_and_slugs(tmp_path: Path) -> None:
    module = _load_linter_module()
    fixture = tmp_path / "invalid_duplicates.yaml"
    fixture.write_text(
        """
- id: dup-1
  slug: dup-slug
  model_family: fam_1
  model_name: First
  description: first
  warnings:
    - watch drift
  references:
    - https://example.com/1
- id: dup-1
  slug: dup-slug
  model_family: fam_2
  model_name: Second
  description: second
  warnings:
    - watch latency
  references:
    - https://example.com/2
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errors = module.lint_catalog_file(fixture)

    assert any("duplicate id 'dup-1'" in err for err in errors)
    assert any("duplicate slug 'dup-slug'" in err for err in errors)


def test_linter_reports_unresolved_reference_placeholders(tmp_path: Path) -> None:
    module = _load_linter_module()
    fixture = tmp_path / "invalid_placeholders.yaml"
    fixture.write_text(
        """
- id: model-1
  slug: model-one
  model_family: family_1
  model_name: Model One
  description: has unresolved reference
  warnings:
    - monitor quality
  references:
    - https://docs.example.com/{{REPLACE_ME}}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errors = module.lint_catalog_file(fixture)

    assert any("unresolved reference placeholder" in err for err in errors)
