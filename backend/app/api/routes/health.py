from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["system"])


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/app/index.html")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
