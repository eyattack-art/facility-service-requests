from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.dependencies import SessionDep

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(response: Response, session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ok"}
