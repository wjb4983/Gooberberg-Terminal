from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "scripts" / "gen-model-adapter.py"

spec = importlib.util.spec_from_file_location("gen_model_adapter", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_model_adapter_snapshot(tmp_path) -> None:
    model_id = "demo_feed"

    module.REPO_ROOT = tmp_path
    module.PROVIDERS_DIR = tmp_path / "services" / "service-data" / "src" / "service_data" / "market_data" / "providers"
    module.TESTS_DIR = tmp_path / "services" / "service-data" / "tests"
    module.DOCS_DIR = tmp_path / "docs" / "model-adapters"
    module.DOCS_INDEX = module.DOCS_DIR / "README.md"

    files = module.generate(model_id)

    rel_files = [path.relative_to(tmp_path).as_posix() for path in files]
    assert rel_files == [
        "services/service-data/src/service_data/market_data/providers/demo_feed_adapter.py",
        "services/service-data/src/service_data/market_data/providers/demo_feed_validation.py",
        "services/service-data/tests/test_demo_feed_adapter_template.py",
        "docs/model-adapters/demo_feed.md",
        "docs/model-adapters/README.md",
    ]

    adapter_text = (module.PROVIDERS_DIR / "demo_feed_adapter.py").read_text(encoding="utf-8")
    assert 'class DemoFeedAdapter(MarketDataProvider):' in adapter_text
    assert 'provider_name = "demo_feed"' in adapter_text

    validation_text = (module.PROVIDERS_DIR / "demo_feed_validation.py").read_text(encoding="utf-8")
    assert "validate_demo_feed_adapter_contract" in validation_text

    test_text = (module.TESTS_DIR / "test_demo_feed_adapter_template.py").read_text(encoding="utf-8")
    assert "test_demo_feed_adapter_provider_name_contract" in test_text

    docs_index_text = module.DOCS_INDEX.read_text(encoding="utf-8")
    assert "- [demo_feed](./demo_feed.md)" in docs_index_text


def test_generate_rejects_existing_file(tmp_path) -> None:
    module.REPO_ROOT = tmp_path
    module.PROVIDERS_DIR = tmp_path / "services" / "service-data" / "src" / "service_data" / "market_data" / "providers"
    module.TESTS_DIR = tmp_path / "services" / "service-data" / "tests"
    module.DOCS_DIR = tmp_path / "docs" / "model-adapters"
    module.DOCS_INDEX = module.DOCS_DIR / "README.md"

    module.PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)
    (module.PROVIDERS_DIR / "demo_feed_adapter.py").write_text("existing", encoding="utf-8")

    try:
        module.generate("demo_feed")
    except module.GenerationError as exc:
        assert "Refusing to overwrite existing file" in str(exc)
    else:
        raise AssertionError("expected GenerationError")
