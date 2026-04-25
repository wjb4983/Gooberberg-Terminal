import hashlib
import json
from dataclasses import asdict, dataclass

from app.schemas.market_data import MarketDataIngestionRequest


@dataclass(frozen=True)
class CanonicalDatasetSpec:
    provider: str
    asset_class: str
    universe_members: tuple[str, ...]
    date_range: dict[str, str]
    resolution_set: tuple[str, ...]
    feature_recipe_version: str
    label_recipe_version: str


def build_canonical_dataset_spec(payload: MarketDataIngestionRequest) -> CanonicalDatasetSpec:
    return CanonicalDatasetSpec(
        provider=payload.provider,
        asset_class=payload.asset_class,
        universe_members=tuple(sorted(set(payload.universe_members))),
        date_range={
            "start": payload.start_date.isoformat(),
            "end": payload.end_date.isoformat(),
        },
        resolution_set=tuple(sorted(set(payload.resolutions))),
        feature_recipe_version=payload.feature_recipe_version,
        label_recipe_version=payload.label_recipe_version,
    )


def serialize_canonical_dataset_spec(spec: CanonicalDatasetSpec) -> str:
    return json.dumps(asdict(spec), sort_keys=True, separators=(",", ":"))


def dataset_id_from_spec(payload: MarketDataIngestionRequest, *, prefix: str = "mds") -> tuple[str, str]:
    spec = build_canonical_dataset_spec(payload)
    serialized = serialize_canonical_dataset_spec(spec)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}", serialized
