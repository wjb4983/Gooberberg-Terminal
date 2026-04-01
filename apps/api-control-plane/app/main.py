import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from app.api.routers.graph import router as graph_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.models import router as models_router
from app.api.routers.portfolio import router as portfolio_router
from app.api.routers.ws import router as ws_router
from app.api.routers.strategies import router as strategies_router
from app.core.config import get_settings
from app.core.logging import RequestIDMiddleware, configure_logging
from app.jobs.redis_queue import lifespan_redis
from app.portfolio import lifespan_portfolio_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
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

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(models_router, prefix=settings.api_prefix)
    app.include_router(graph_router, prefix=settings.api_prefix)
    app.include_router(portfolio_router, prefix=settings.api_prefix)
    app.include_router(strategies_router, prefix=settings.api_prefix)
    app.include_router(ws_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    logger.info("api control-plane app initialized")
    return app


app = create_app()
