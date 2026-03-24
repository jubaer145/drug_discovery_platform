import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from models.schemas import AdmetRequest, AdmetResponse

router = APIRouter()


@router.post("/predict", response_model=AdmetResponse)
async def predict_admet(
    request: AdmetRequest,
    db: AsyncSession = Depends(get_session),
) -> AdmetResponse:
    """Dispatch ADMET prediction job — implemented in Sprint 5."""
    job_id = str(uuid.uuid4())
    # TODO Sprint 5: dispatch run_admet.delay(job_id, request.smiles_list)
    return AdmetResponse(job_id=job_id, status="pending")
