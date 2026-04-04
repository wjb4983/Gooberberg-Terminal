from app.domain.graph_domain.repository import Repository
from app.schemas import GraphTopologyResponse


class Service:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def get_topology(self) -> GraphTopologyResponse:
        return self._repository.get_topology()
