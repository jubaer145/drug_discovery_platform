from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from core.pipeline import dispatch_pipeline
from models.schemas import PipelineRequest, PipelineResponse

router = APIRouter()


@router.post("/run", response_model=PipelineResponse)
async def run_pipeline(
    request: PipelineRequest,
    db: AsyncSession = Depends(get_session),
) -> PipelineResponse:
    """Dispatch full pipeline job. Returns job_id immediately."""
    return await dispatch_pipeline(request, db)
