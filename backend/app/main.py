from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.api import get_api_router
from app.core.config import get_settings
from app.db.base import Base  # noqa: F401  ensures models are imported
from app.db.session import engine


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(get_api_router())

    application.mount(
        "/app",
        StaticFiles(directory=str(settings.frontend_directory), html=True),
        name="frontend",
    )

    @application.on_event("startup")
    def _startup() -> None:
        # Fast path for local dev. Production deployments should rely on Alembic migrations.
        if settings.database_url.startswith("sqlite"):
            Base.metadata.create_all(bind=engine)

    return application


app = create_application()
