import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session

router = APIRouter()


@router.post("/generate")
async def generate_molecules(
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Dispatch de novo molecule generation job — implemented in Sprint 4."""
    job_id = str(uuid.uuid4())
    return {"job_id": job_id, "status": "pending"}
