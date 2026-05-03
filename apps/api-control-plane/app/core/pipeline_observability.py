from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager

from app.schemas.graph import PipelineResponseMetadata

logger = logging.getLogger("app.pipeline")


class PipelineResponseMeta(PipelineResponseMetadata):
    pass


@contextmanager
def observe_pipeline_stage(
    *,
    stage: str,
    fingerprint_source: dict[str, object],
    fallback_reason: str | None = None,
    metric_hook: Callable[[str, float, bool], None] | None = None,
):
    started = time.monotonic()
    success = False
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_source, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    try:
        yield fingerprint
        success = True
    finally:
        duration_ms = (time.monotonic() - started) * 1000
        logger.info(
            "pipeline stage",
            extra={
                "stage": stage,
                "duration_ms": round(duration_ms, 3),
                "success": success,
                "fingerprint": fingerprint,
                "fallback_reason": fallback_reason,
            },
        )
        if metric_hook:
            metric_hook(stage, duration_ms, success)
