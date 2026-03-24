import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from models.schemas import DockingRequest, DockingResponse

router = APIRouter()


@router.post("/run", response_model=DockingResponse)
async def run_docking(
    request: DockingRequest,
    db: AsyncSession = Depends(get_session),
) -> DockingResponse:
    """Dispatch docking job — implemented in Sprint 4."""
    job_id = str(uuid.uuid4())
    # TODO Sprint 4: dispatch run_docking.delay(job_id, request.target_pdb_path, request.molecules)
    return DockingResponse(job_id=job_id, status="pending")
