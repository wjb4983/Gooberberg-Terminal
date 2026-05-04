from collections.abc import Generator
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings

logger = logging.getLogger(__name__)
HEAD_REVISION = "20260430_0006"
LEGACY_APP_TABLES = (
    "model_configs",
    "training_runs",
    "parameter_sweep_runs",
    "backtest_runs",
    "testing_runs",
    "run_artifacts",
)
LEGACY_REPAIR_SQL = {
    "training_runs": (
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS task_type VARCHAR(64) NOT NULL DEFAULT 'time_series_momentum'",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS subtask_type VARCHAR(64) NOT NULL DEFAULT 'ranking'",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS dataset_spec_hash VARCHAR(128) NOT NULL DEFAULT ''",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS dataset_manifest_version VARCHAR(64) NOT NULL DEFAULT 'v1'",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS resolved_symbol_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS resolved_member_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS model_config_version_tag VARCHAR(64) NOT NULL DEFAULT 'unknown'",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS constraint_profile_version VARCHAR(64) NOT NULL DEFAULT 'v1'",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS lineage_version INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS dataset_fingerprint VARCHAR(128)",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS code_hash VARCHAR(64)",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS config_digest VARCHAR(128)",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS seed INTEGER",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS lineage_status VARCHAR(32)",
        "ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS lineage_error_code VARCHAR(64)",
    ),
    "parameter_sweep_runs": (
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS parameter_set_id VARCHAR(36)",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS task_type VARCHAR(64) NOT NULL DEFAULT 'time_series_momentum'",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS subtask_type VARCHAR(64) NOT NULL DEFAULT 'ranking'",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS provenance_snapshot JSON NOT NULL DEFAULT '{}'::json",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS lineage_version INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS dataset_fingerprint VARCHAR(128)",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS code_hash VARCHAR(64)",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS config_digest VARCHAR(128)",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS seed INTEGER",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS lineage_status VARCHAR(32)",
        "ALTER TABLE parameter_sweep_runs ADD COLUMN IF NOT EXISTS lineage_error_code VARCHAR(64)",
    ),
    "backtest_runs": (
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS deterministic_mode BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS scenario_id VARCHAR(64) NOT NULL DEFAULT 'baseline'",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS git_sha VARCHAR(64) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS config_hash VARCHAR(128) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS data_snapshot_id VARCHAR(128) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS random_seed INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS engine_version VARCHAR(64) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS feature_set_version VARCHAR(64) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT 'UTC'",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS calendar_id VARCHAR(64) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS resolved_config JSON NOT NULL DEFAULT '{}'::json",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS environment_fingerprint JSON NOT NULL DEFAULT '{}'::json",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS run_checksum VARCHAR(128) NOT NULL DEFAULT ''",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS lineage_version INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS dataset_fingerprint VARCHAR(128)",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS code_hash VARCHAR(64)",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS config_digest VARCHAR(128)",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS seed INTEGER",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS lineage_status VARCHAR(32)",
        "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS lineage_error_code VARCHAR(64)",
    ),
    "testing_runs": (
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS lineage_version INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS dataset_fingerprint VARCHAR(128)",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS code_hash VARCHAR(64)",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS config_digest VARCHAR(128)",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS seed INTEGER",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS lineage_status VARCHAR(32)",
        "ALTER TABLE testing_runs ADD COLUMN IF NOT EXISTS lineage_error_code VARCHAR(64)",
    ),
    "run_artifacts": (
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS checksum VARCHAR(128) NOT NULL DEFAULT ''",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS size_bytes INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS retention_class VARCHAR(32) NOT NULL DEFAULT 'standard'",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS signature VARCHAR(256) NOT NULL DEFAULT ''",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS promotion_status VARCHAR(32) NOT NULL DEFAULT 'draft'",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS artifact_role VARCHAR(64) NOT NULL DEFAULT 'unspecified'",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS artifact_uri VARCHAR(1024) NOT NULL DEFAULT ''",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS sha256 VARCHAR(64) NOT NULL DEFAULT ''",
        "ALTER TABLE run_artifacts ADD COLUMN IF NOT EXISTS content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream'",
        "UPDATE run_artifacts SET checksum = artifact_ref WHERE checksum = '' OR checksum IS NULL",
        "UPDATE run_artifacts SET artifact_uri = artifact_ref WHERE artifact_uri = '' OR artifact_uri IS NULL",
        "UPDATE run_artifacts SET sha256 = repeat('0', 64) WHERE sha256 = '' OR sha256 IS NULL",
    ),
}


def normalize_dsn(raw_dsn: str | None) -> str:
    dsn = raw_dsn or "sqlite+pysqlite:///:memory:"
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+psycopg://", 1)
    return dsn


def run_database_migrations(settings: Settings) -> None:
    dsn = normalize_dsn(settings.postgres_dsn)
    if dsn.startswith("sqlite"):
        return

    engine = create_engine(dsn, pool_pre_ping=True, future=True)
    try:
        inspector = inspect(engine)
        alembic_config = _build_alembic_config(dsn)

        if inspector.has_table("alembic_version"):
            logger.info("running alembic migrations")
            command.upgrade(alembic_config, "head")
            logger.info("alembic migrations complete")
            return

        if _has_legacy_schema(inspector):
            logger.info("repairing legacy postgres schema before alembic stamp")
            _repair_legacy_schema(engine)
            command.stamp(alembic_config, HEAD_REVISION)
            logger.info("legacy postgres schema repaired and stamped at %s", HEAD_REVISION)
            return

        logger.info("running alembic migrations")
        command.upgrade(alembic_config, "head")
        logger.info("alembic migrations complete")
    finally:
        engine.dispose()


def _build_alembic_config(dsn: str) -> Config:
    project_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(project_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(project_root / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", dsn)
    return alembic_config


def _has_legacy_schema(inspector) -> bool:
    return any(inspector.has_table(table_name) for table_name in LEGACY_APP_TABLES)


def _repair_legacy_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        for table_name, statements in LEGACY_REPAIR_SQL.items():
            if not _table_exists(connection, table_name):
                continue
            for statement in statements:
                connection.execute(text(statement))


def _table_exists(connection: Connection, table_name: str) -> bool:
    return inspect(connection).has_table(table_name)


class Database:
    def __init__(self, settings: Settings) -> None:
        dsn = normalize_dsn(settings.postgres_dsn)
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
