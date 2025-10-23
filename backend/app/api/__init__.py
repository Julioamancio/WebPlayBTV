from fastapi import APIRouter

from app.api.routes import auth, catalog, devices, health, licenses, stream


def get_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(licenses.router)
    router.include_router(devices.router)
    router.include_router(catalog.router)
    router.include_router(stream.router)
    return router

