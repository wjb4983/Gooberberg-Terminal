from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        dsn = settings.postgres_dsn or "sqlite+pysqlite:///:memory:"
        if dsn.startswith("sqlite"):
            self.engine = create_engine(
                dsn,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                future=True,
            )
        else:
            self.engine = create_engine(dsn, pool_pre_ping=True, future=True)

        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session


def create_database(settings: Settings) -> Database:
    return Database(settings)
