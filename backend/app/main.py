from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db import create_db_and_tables
from app.observability import metrics_middleware
from app.config import CORS_ALLOW_ORIGINS
from app.routers.auth import router as auth_router
from app.routers.devices import router as devices_router
from app.routers.catalog import router as catalog_router
from app.routers.metrics import router as metrics_router
from app.routers.epg import router as epg_router
from app.routers.licenses import router as licenses_router
from app.routers.audit import router as audit_router
from app.routers.ui import router as ui_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    yield
    # Shutdown (opcional)

app = FastAPI(title="WebPlay Backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(catalog_router)
app.include_router(metrics_router)
app.include_router(epg_router)
app.include_router(licenses_router)
app.include_router(audit_router)
app.include_router(ui_router)

## Removido on_event(deprecated); usando Lifespan acima


@app.middleware("http")
async def _metrics_middleware(request, call_next):
    return await metrics_middleware(request, call_next)

# CORS
origins_cfg = CORS_ALLOW_ORIGINS
if isinstance(origins_cfg, str):
    if origins_cfg.strip() == "*":
        allow_origins = ["*"]
    else:
        allow_origins = [o.strip() for o in origins_cfg.split(",") if o.strip()]
else:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
