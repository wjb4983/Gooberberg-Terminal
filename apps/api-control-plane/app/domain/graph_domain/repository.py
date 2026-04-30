from app.core.config import get_settings
from app.persistence.repositories import GraphSqlRepository
from app.schemas import GraphTopologyResponse


class Repository:
    def __init__(self, sql_repository: GraphSqlRepository) -> None:
        self._repository = sql_repository

    def get_topology(self) -> GraphTopologyResponse:
        settings = get_settings()
        self._repository.ensure_seeded_from_entities(
            allow_mock_fallback=not settings.graph_prod_topology_enabled,
            force_mock_topology=settings.graph_mock_topology_enabled,
            environment=settings.environment,
        )
        return self._repository.get_topology()
