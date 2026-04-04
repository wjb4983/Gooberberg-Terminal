from app.graph.mock_provider import get_mock_topology
from app.persistence.repositories import GraphSqlRepository
from app.schemas import GraphTopologyResponse


class Repository:
    def __init__(self, sql_repository: GraphSqlRepository) -> None:
        self._repository = sql_repository

    def get_topology(self) -> GraphTopologyResponse:
        self._repository.ensure_seeded(get_mock_topology())
        return self._repository.get_topology()
