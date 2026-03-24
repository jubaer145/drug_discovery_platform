import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session
from models.schemas import StructurePredictRequest, StructurePredictResponse

router = APIRouter()


@router.post("/predict", response_model=StructurePredictResponse)
async def predict_structure(
    request: StructurePredictRequest,
    db: AsyncSession = Depends(get_session),
) -> StructurePredictResponse:
    """Dispatch structure prediction job — implemented in Sprint 3."""
    job_id = str(uuid.uuid4())
    # TODO Sprint 3: dispatch run_structure_prediction.delay(job_id, request.sequence, request.method)
    return StructurePredictResponse(job_id=job_id, status="pending")
