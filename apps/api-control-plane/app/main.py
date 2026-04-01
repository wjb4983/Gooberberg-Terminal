import logging

from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.ws import router as ws_router
from app.core.config import get_settings
from app.core.logging import RequestIDMiddleware, configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(RequestIDMiddleware)

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(ws_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    logger.info("api control-plane app initialized")
    return app


app = create_app()
