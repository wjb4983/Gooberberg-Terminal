from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/audit", tags=["audit"])


class LineageLink(BaseModel):
    rel: str
    href: str
    source_type: str
    source_id: str


class StrategyProvenance(BaseModel):
    strategy_id: str
    strategy_version: str
    config_digest: str
    config_version: str


class RiskOutcome(BaseModel):
    decision: str
    policy: str
    reasons: list[str]
    max_notional: float
    max_quantity: float


class ExecutionLatencyDetails(BaseModel):
    venue: str
    order_type: str
    route: str
    queued_at: datetime
    sent_at: datetime
    acked_at: datetime
    completed_at: datetime
    total_latency_ms: int = Field(ge=0)
    exchange_latency_ms: int = Field(ge=0)
    broker_latency_ms: int = Field(ge=0)


class AuditEnvelope(BaseModel):
    id: str
    entity_type: str
    observed_at: datetime
    created_at: datetime
    updated_at: datetime
    lineage_links: list[LineageLink]
    provenance: StrategyProvenance
    risk_outcome: RiskOutcome
    execution: ExecutionLatencyDetails


def _build_audit_envelope(entity_type: str, entity_id: str) -> AuditEnvelope:
    now = datetime.now(UTC)
    return AuditEnvelope(
        id=entity_id,
        entity_type=entity_type,
        observed_at=now,
        created_at=now,
        updated_at=now,
        lineage_links=[
            LineageLink(
                rel="originating_run",
                href=f"/api/v1/runs/{entity_id}/lineage",
                source_type="run",
                source_id=entity_id,
            ),
            LineageLink(
                rel="replay_bundle",
                href=f"/api/v1/runs/{entity_id}/replay",
                source_type="run",
                source_id=entity_id,
            ),
        ],
        provenance=StrategyProvenance(
            strategy_id="mean-reversion-alpha",
            strategy_version="2026.04.30",
            config_digest=f"sha256:{entity_id.replace('-', '')[:16]}",
            config_version="risk-profile-v3",
        ),
        risk_outcome=RiskOutcome(
            decision="approved",
            policy="global-risk-policy",
            reasons=["position_within_limits", "volatility_band_permits_execution"],
            max_notional=250000.0,
            max_quantity=1500.0,
        ),
        execution=ExecutionLatencyDetails(
            venue="paper-sim",
            order_type="limit",
            route="smart-router",
            queued_at=now,
            sent_at=now,
            acked_at=now,
            completed_at=now,
            total_latency_ms=18,
            exchange_latency_ms=9,
            broker_latency_ms=4,
        ),
    )


@router.get("/decisions/{decision_id}", response_model=AuditEnvelope)
async def get_audit_decision(decision_id: UUID) -> AuditEnvelope:
    return _build_audit_envelope("decision", str(decision_id))


@router.get("/orders/{order_id}", response_model=AuditEnvelope)
async def get_audit_order(order_id: UUID) -> AuditEnvelope:
    return _build_audit_envelope("order", str(order_id))


@router.get("/fills/{fill_id}", response_model=AuditEnvelope)
async def get_audit_fill(fill_id: UUID) -> AuditEnvelope:
    return _build_audit_envelope("fill", str(fill_id))


@router.get("/traces/{trace_id}", response_model=AuditEnvelope)
async def get_audit_trace(trace_id: UUID) -> AuditEnvelope:
    return _build_audit_envelope("trace", str(trace_id))


@router.get("/events")
async def list_audit_events(filters: str = Query(default="")) -> dict[str, object]:
    event = _build_audit_envelope("event", "event-0001")
    return {"filters": filters, "events": [event.model_dump(mode="json")]}


@router.get("/replay")
async def get_audit_replay(trace_id: UUID | None = None, order_id: UUID | None = None) -> dict[str, object]:
    replay_target = str(trace_id or order_id or "replay-session")
    envelope = _build_audit_envelope("replay", replay_target)
    return {
        "replay_id": replay_target,
        "lineage_links": [link.model_dump() for link in envelope.lineage_links],
        "timestamps": {
            "observed_at": envelope.observed_at,
            "created_at": envelope.created_at,
            "updated_at": envelope.updated_at,
        },
        "provenance": envelope.provenance.model_dump(),
        "risk_outcome": envelope.risk_outcome.model_dump(),
        "execution": envelope.execution.model_dump(mode="json"),
    }
