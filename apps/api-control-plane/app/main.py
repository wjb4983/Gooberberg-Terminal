import logging
from datetime import datetime
from collections.abc import AsyncIterator
from collections.abc import Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from app.api.routers.alerts import router as alerts_router
from app.api.routers.backtest_runs import router as backtest_runs_router
from app.api.routers.graph import router as graph_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.market_data import router as market_data_router
from app.api.routers.model_configs import router as model_configs_router
from app.api.routers.models import router as models_router
from app.api.routers.parameter_sweeps import router as parameter_sweeps_router
from app.api.routers.parameter_sets import router as parameter_sets_router
from app.api.routers.portfolio import router as portfolio_router
from app.api.routers.risk import router as risk_router
from app.api.routers.ws import router as ws_router
from app.api.routers.strategies import router as strategies_router
from app.api.routers.testing_runs import router as testing_runs_router
from app.api.routers.training_runs import router as training_runs_router
from app.core.config import get_settings
from app.core.auth import BearerTokenAuthMiddleware
from app.core.logging import RequestIDMiddleware, configure_logging
from app.domain.job_runner import JobRunnerRepository, JobRunnerService
from app.persistence import create_database
from app.persistence.job_events import JobEventRepository
from app.persistence.models import Base
from app.domain.model_configs import HmmRegimeSwitchingModelSpec
from app.domain.model_registry import ModelRegistry
from app.domain.task_registry import TaskRegistry
from app.jobs.redis_queue import lifespan_redis
from app.portfolio import lifespan_portfolio_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        model_registry = ModelRegistry()
        model_registry.register(HmmRegimeSwitchingModelSpec())
        task_registry = TaskRegistry()

        async def _noop_task_runner(payload: Mapping[str, object]) -> dict[str, object]:
            return {"accepted": True, "payload_keys": sorted(payload.keys())}

        for task_type in ("training", "parameter_sweep", "backtest", "testing"):
            task_registry.register_runner(task_type, _noop_task_runner)

        database = create_database(get_settings())
        Base.metadata.create_all(database.engine)

        app.state.database = database
        app.state.model_registry = model_registry
        app.state.task_registry = task_registry
        app.state.job_runner_service = JobRunnerService(JobRunnerRepository(), task_registry)
        app.state.job_event_repository = JobEventRepository(app.state.database.session_factory)
        app.state.last_worker_heartbeat_at: datetime | None = None
        await stack.enter_async_context(lifespan_redis(app))
        await stack.enter_async_context(lifespan_portfolio_cache(app))
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=app_lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        BearerTokenAuthMiddleware,
        health_paths={
            f"{settings.api_prefix}/health",
            f"{settings.api_prefix}/health/queue",
            f"{settings.api_prefix}/health/queue/heartbeat",
            "/healthz",
        },
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(alerts_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(models_router, prefix=settings.api_prefix)
    app.include_router(model_configs_router, prefix=settings.api_prefix)
    app.include_router(training_runs_router, prefix=settings.api_prefix)
    app.include_router(testing_runs_router, prefix=settings.api_prefix)
    app.include_router(parameter_sweeps_router, prefix=settings.api_prefix)
    app.include_router(parameter_sets_router, prefix=settings.api_prefix)
    app.include_router(backtest_runs_router, prefix=settings.api_prefix)
    app.include_router(market_data_router, prefix=settings.api_prefix)
    app.include_router(graph_router, prefix=settings.api_prefix)
    app.include_router(portfolio_router, prefix=settings.api_prefix)
    app.include_router(strategies_router, prefix=settings.api_prefix)
    app.include_router(risk_router, prefix=settings.api_prefix)
    app.include_router(ws_router)


    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    logger.info("api control-plane app initialized")
    return app


app = create_app()
