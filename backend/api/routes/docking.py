import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.queue import run_docking
from models.schemas import DockingRequest, DockingResponse

router = APIRouter()


@router.post("/run", response_model=DockingResponse)
async def run_docking_endpoint(
    request: DockingRequest,
    db: AsyncSession = Depends(get_session),
) -> DockingResponse:
    """Dispatch docking job as a background task."""
    job_id = str(uuid.uuid4())

    input_data = {
        "pdb_path": request.target_pdb_path,
        "smiles_list": request.molecules,
        "binding_site": request.binding_site,
        "exhaustiveness": request.exhaustiveness,
    }

    run_docking.delay(job_id, input_data)
    return DockingResponse(job_id=job_id, status="pending")
