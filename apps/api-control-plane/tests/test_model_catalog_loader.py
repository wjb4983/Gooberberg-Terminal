from pathlib import Path

import pytest

from app.domain.model_catalog.loader import load_model_metadata_from_directory


CATALOG_DIRECTORY = Path(__file__).resolve().parents[3] / "config" / "models" / "catalog"


def test_catalog_fixtures_validate_successfully() -> None:
    entries = load_model_metadata_from_directory(CATALOG_DIRECTORY)
    fixture_files = sorted(CATALOG_DIRECTORY.glob("*.yaml"))

    assert fixture_files
    assert entries
    assert len(entries) == len(fixture_files)
    assert all(entry.required_data for entry in entries)


def test_catalog_loader_rejects_invalid_metadata_with_explicit_error(tmp_path: Path) -> None:
    fixture = tmp_path / "broken.json"
    fixture.write_text(
        '[{"model_family":"demo","model_name":"Demo","description":"x","required_data":["a"],"compute_intensity":"extreme","output_schema":"schema.v1"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        load_model_metadata_from_directory(tmp_path)

    message = str(exc_info.value)
    assert "compute_intensity" in message
    assert "broken.json" in message


def test_catalog_loader_rejects_duplicate_families(tmp_path: Path) -> None:
    (tmp_path / "first.json").write_text(
        '[{"model_family":"demo","model_name":"Demo","description":"x","required_data":["a"],"output_schema":"schema.v1"}]',
        encoding="utf-8",
    )
    (tmp_path / "second.json").write_text(
        '[{"model_family":"demo","model_name":"Demo2","description":"x","required_data":["b"],"output_schema":"schema.v1"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"duplicate model_family 'demo'.*second\.json.*first\.json"):
        load_model_metadata_from_directory(tmp_path)


def test_catalog_loader_accepts_valid_taxonomy_values(tmp_path: Path) -> None:
    (tmp_path / "ok.yaml").write_text(
        """
- model_family: demo
  model_name: Demo
  description: x
  required_data: [a]
  output_schema: schema.v1
  phase: phase1
  family: forecasting
  subfamily: linear
  targets: [point]
  horizons: [daily]
  maturity: beta
  complexity: medium
""",
        encoding="utf-8",
    )

    entries = load_model_metadata_from_directory(tmp_path)
    assert len(entries) == 1


def test_catalog_loader_rejects_invalid_taxonomy_values_with_clear_error(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text(
        """
- model_family: demo
  model_name: Demo
  description: x
  required_data: [a]
  output_schema: schema.v1
  phase: phase9
  targets: [point, forever]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        load_model_metadata_from_directory(tmp_path)

    message = str(exc_info.value)
    assert "invalid taxonomy value for phase" in message
    assert "phase9" in message
    assert "Allowed values" in message
    assert "bad.yaml" in message
