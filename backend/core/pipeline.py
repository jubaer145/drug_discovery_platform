import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import PipelineRequest, PipelineResponse
from core.queue import run_pipeline


async def dispatch_pipeline(request: PipelineRequest, db: AsyncSession) -> PipelineResponse:
    """
    Orchestrates the pipeline by dispatching a Celery task.
    Returns job_id immediately — never blocks on computation.
    """
    job_id = str(uuid.uuid4())
    run_pipeline.delay(job_id, request.model_dump())
    return PipelineResponse(job_id=job_id, status="pending")
