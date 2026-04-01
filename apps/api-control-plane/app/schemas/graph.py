from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GraphNodeType(StrEnum):
    STRATEGY = "strategy"
    MODEL = "model"
    DATA_SOURCE = "data_source"
    RISK_RULE = "risk_rule"
    EXECUTION_ADAPTER = "execution_adapter"
    JOB = "job"


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    group: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class GraphTopologyResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
