from fastapi import APIRouter

from app.db import check_db_health
from app.schemas import HealthResponse

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        check_db_health()
        return HealthResponse(status="ok", database="ok")
    except Exception:
        return HealthResponse(status="degraded", database="error")
