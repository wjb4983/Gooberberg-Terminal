from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from service_data.main import (
    DataRefsQuery,
    MarketDataRef,
    TimeRange,
    get_data_ref,
    query_data_refs,
)


def test_market_data_ref_uri_must_point_to_data_lake() -> None:
    with pytest.raises(ValidationError):
        MarketDataRef(
            ref_id=uuid4(),
            format="parquet",
            uri="file:///tmp/outside-lake.parquet",
            schema_hash="sha256:validhash",
            time_range=TimeRange.model_validate(
                {
                    "start": "2026-03-31T13:30:00Z",
                    "end": "2026-03-31T20:00:00Z",
                }
            ),
            symbols=["AAPL"],
        )


def test_query_returns_metadata_refs_only() -> None:
    refs = query_data_refs(
        DataRefsQuery(
            symbols=["AAPL"],
            start=datetime(2026, 3, 31, 0, 0, tzinfo=timezone.utc),
        )
    )

    assert len(refs) >= 1
    first = refs[0].model_dump()
    assert set(first.keys()) == {
        "ref_id",
        "format",
        "uri",
        "schema_hash",
        "time_range",
        "symbols",
    }


def test_get_ref_by_id_returns_record() -> None:
    refs = query_data_refs(DataRefsQuery())
    ref_id = UUID(str(refs[0].ref_id))

    result = get_data_ref(ref_id)

    assert result.ref_id == ref_id
