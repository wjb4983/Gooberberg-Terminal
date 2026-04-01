from pydantic import BaseModel


class DependencyStatus(BaseModel):
    configured: bool
    reachable: bool | None = None
    detail: str


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str
    postgres: DependencyStatus
    redis: DependencyStatus
