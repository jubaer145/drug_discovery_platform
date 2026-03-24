import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from models.schemas import TargetLookupRequest, TargetLookupResponse

router = APIRouter()


@router.post("/lookup", response_model=TargetLookupResponse)
async def lookup_target(
    request: TargetLookupRequest,
    db: AsyncSession = Depends(get_session),
) -> TargetLookupResponse:
    """Dispatch target lookup job — implemented in Sprint 1."""
    job_id = str(uuid.uuid4())
    # TODO Sprint 1: dispatch run_target_lookup.delay(job_id, request.query, request.user_id)
    return TargetLookupResponse(job_id=job_id, status="pending")
