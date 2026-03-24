import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session

router = APIRouter()


@router.post("/protein")
async def design_protein(
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Dispatch protein design job — implemented in Sprint 3."""
    job_id = str(uuid.uuid4())
    return {"job_id": job_id, "status": "pending"}
