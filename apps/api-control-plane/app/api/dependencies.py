from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.domain.backtest_runs import Repository as BacktestRunRepository
from app.domain.backtest_runs import Service as BacktestRunService
from app.domain.graph_domain import Repository as GraphRepository
from app.domain.graph_domain import Service as GraphService
from app.domain.job_runner import JobRunnerService
from app.domain.market_data import Repository as MarketDataRepository
from app.domain.market_data import Service as MarketDataService
from app.domain.model_configs import ModelConfigRepository, ModelConfigService
from app.domain.model_catalog import ModelCatalogRegistry
from app.domain.model_registry import ModelRegistry
from app.domain.parameter_sweeps import Repository as ParameterSweepRepository
from app.domain.parameter_sweeps import Service as ParameterSweepService
from app.domain.parameter_sets import Repository as ParameterSetRepository
from app.domain.parameter_sets import Service as ParameterSetService
from app.domain.task_registry import TaskRegistry
from app.domain.testing_runs import Repository as TestingRunRepository
from app.domain.testing_runs import Service as TestingRunService
from app.domain.training_runs import Repository as TrainingRunRepository
from app.domain.training_runs import Service as TrainingRunService
from app.persistence.models import BacktestRunRow, ParameterSweepRunRow, TestingRunRow, TrainingRunRow
from app.persistence.repositories import GraphSqlRepository, MarketDataSqlRepository, RunSqlRepository


def get_db_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.database.session_factory() as session:
        yield session


def get_model_registry(request: Request) -> ModelRegistry:
    return request.app.state.model_registry


def get_model_catalog_registry(request: Request) -> ModelCatalogRegistry:
    return request.app.state.model_catalog_registry


def get_task_registry(request: Request) -> TaskRegistry:
    return request.app.state.task_registry


def get_job_runner_service(request: Request) -> JobRunnerService:
    return request.app.state.job_runner_service


def get_model_config_service(request: Request, session: Session = Depends(get_db_session)) -> ModelConfigService:
    return ModelConfigService(ModelConfigRepository(session), request.app.state.model_registry)


def get_training_run_service(session: Session = Depends(get_db_session)) -> TrainingRunService:
    return TrainingRunService(TrainingRunRepository(RunSqlRepository(session, TrainingRunRow)))


def get_parameter_sweep_service(session: Session = Depends(get_db_session)) -> ParameterSweepService:
    return ParameterSweepService(ParameterSweepRepository(RunSqlRepository(session, ParameterSweepRunRow)))


def get_parameter_set_service(session: Session = Depends(get_db_session)) -> ParameterSetService:
    return ParameterSetService(ParameterSetRepository(session))


def get_backtest_run_service(session: Session = Depends(get_db_session)) -> BacktestRunService:
    return BacktestRunService(BacktestRunRepository(RunSqlRepository(session, BacktestRunRow)))


def get_testing_run_service(session: Session = Depends(get_db_session)) -> TestingRunService:
    return TestingRunService(TestingRunRepository(RunSqlRepository(session, TestingRunRow)))


def get_graph_service(session: Session = Depends(get_db_session)) -> GraphService:
    return GraphService(GraphRepository(GraphSqlRepository(session)))


def get_market_data_service(session: Session = Depends(get_db_session)) -> MarketDataService:
    return MarketDataService(MarketDataRepository(MarketDataSqlRepository(session)))
