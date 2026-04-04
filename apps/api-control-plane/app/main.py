import logging
from collections.abc import AsyncIterator
from collections.abc import Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from app.api.routers.alerts import router as alerts_router
from app.api.routers.graph import router as graph_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.models import router as models_router
from app.api.routers.portfolio import router as portfolio_router
from app.api.routers.risk import router as risk_router
from app.api.routers.ws import router as ws_router
from app.api.routers.strategies import router as strategies_router
from app.core.config import get_settings
from app.core.auth import BearerTokenAuthMiddleware
from app.core.logging import RequestIDMiddleware, configure_logging
from app.domain.job_runner import JobRunnerRepository, JobRunnerService
from app.domain.model_configs import HmmRegimeSwitchingModelSpec, ModelConfigRepository, ModelConfigService
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

        for task_type in ("training", "parameter_sweep", "backtest"):
            task_registry.register_runner(task_type, _noop_task_runner)

        app.state.model_registry = model_registry
        app.state.task_registry = task_registry
        app.state.model_config_service = ModelConfigService(ModelConfigRepository(), model_registry)
        app.state.job_runner_service = JobRunnerService(JobRunnerRepository(), task_registry)
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
    app.add_middleware(BearerTokenAuthMiddleware, health_paths={f"{settings.api_prefix}/health", "/healthz"})

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(alerts_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(models_router, prefix=settings.api_prefix)
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
