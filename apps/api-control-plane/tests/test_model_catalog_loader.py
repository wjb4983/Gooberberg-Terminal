from pathlib import Path

import pytest

from app.domain.model_catalog.loader import load_model_metadata_from_directory


CATALOG_DIRECTORY = Path(__file__).resolve().parents[1] / "app" / "domain" / "model_catalog" / "catalog"


def test_catalog_fixtures_validate_successfully() -> None:
    entries = load_model_metadata_from_directory(CATALOG_DIRECTORY)
    assert entries
    assert all(entry.required_data for entry in entries)


def test_catalog_loader_rejects_invalid_metadata_with_explicit_error(tmp_path: Path) -> None:
    fixture = tmp_path / "broken.json"
    fixture.write_text(
        '[{"model_family":"demo","model_name":"Demo","description":"x","required_data":["a"],"compute_intensity":"extreme","output_schema":"schema.v1"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"compute_intensity.*broken\.json.*item index 0"):
        load_model_metadata_from_directory(tmp_path)


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
