import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from models.schemas import AIQueryRequest, AIQueryResponse

router = APIRouter()


@router.post("/suggest-targets", response_model=AIQueryResponse)
async def suggest_targets(
    request: AIQueryRequest,
    db: AsyncSession = Depends(get_session),
) -> AIQueryResponse:
    """Dispatch AI query job — implemented in Sprint 2."""
    job_id = str(uuid.uuid4())
    # TODO Sprint 2: dispatch run_ai_query.delay(job_id, request.disease_description, request.user_id)
    return AIQueryResponse(job_id=job_id, status="pending")
