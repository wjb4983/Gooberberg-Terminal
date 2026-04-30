from app.core.config import get_settings
from app.graph.mock_provider import get_mock_topology
from app.persistence.repositories import GraphSqlRepository
from app.schemas import GraphTopologyResponse


class Repository:
    def __init__(self, sql_repository: GraphSqlRepository) -> None:
        self._repository = sql_repository

    def get_topology(self) -> GraphTopologyResponse:
        settings = get_settings()
        if settings.graph_mock_topology_enabled:
            self._repository.ensure_seeded(get_mock_topology())
        else:
            self._repository.ensure_seeded_from_entities()
        return self._repository.get_topology()
