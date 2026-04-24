import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import get_settings
from app.etl.router import router as etl_router
from app.review.router import router as review_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the ARQ connection pool on startup (if ``REDIS_URL`` is set) and
    close it on shutdown. When Redis isn't configured the pool stays ``None``
    and ``get_arq_pool`` returns 503 — useful for local dev that doesn't need
    background jobs.
    """
    settings = get_settings()
    app.state.arq_pool = None
    if settings.redis_url:
        try:
            from arq.connections import RedisSettings, create_pool

            app.state.arq_pool = await create_pool(
                RedisSettings.from_dsn(settings.redis_url)
            )
        except Exception:
            logger.exception("failed to open ARQ pool — ETL endpoints will return 503")
    try:
        yield
    finally:
        if app.state.arq_pool is not None:
            await app.state.arq_pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DeciContas Review API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(review_router)
    app.include_router(etl_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
