from fastapi import FastAPI
from app.db import create_db_and_tables
from app.observability import metrics_middleware
from app.routers.auth import router as auth_router
from app.routers.devices import router as devices_router
from app.routers.catalog import router as catalog_router
from app.routers.metrics import router as metrics_router
from app.routers.epg import router as epg_router

app = FastAPI(title="WebPlay Backend", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(catalog_router)
app.include_router(metrics_router)
app.include_router(epg_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.middleware("http")
async def _metrics_middleware(request, call_next):
    return await metrics_middleware(request, call_next)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

