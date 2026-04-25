from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.market_data.repository import Repository
    from app.domain.market_data.service import Service


def __getattr__(name: str) -> object:
    if name == "Repository":
        from app.domain.market_data.repository import Repository

        return Repository
    if name == "Service":
        from app.domain.market_data.service import Service

        return Service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["Repository", "Service"]
