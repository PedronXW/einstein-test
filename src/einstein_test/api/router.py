from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from einstein_test.api.dependencies import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Healthcheck simples da API (leve: apenas um SELECT)."""
    session.execute(text("SELECT 1"))
    return {"status": "ok"}