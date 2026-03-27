import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.queue import run_structure_prediction
from core.storage import download_file, file_exists
from models.schemas import StructurePredictRequest, StructurePredictResponse

router = APIRouter()


@router.post("/predict", response_model=StructurePredictResponse)
async def predict_structure(
    request: StructurePredictRequest,
    db: AsyncSession = Depends(get_session),
) -> StructurePredictResponse:
    """Dispatch structure prediction as a background job."""
    job_id = str(uuid.uuid4())
    run_structure_prediction.delay(job_id, request.sequence, request.sequence_name)
    return StructurePredictResponse(job_id=job_id, status="pending")


@router.get("/{job_id}/download")
async def download_structure(job_id: str) -> Response:
    """Stream the predicted PDB file from MinIO."""
    key = f"{job_id}/predicted.pdb"
    if not file_exists("structures", key):
        raise HTTPException(status_code=404, detail="Structure file not found")

    data = download_file("structures", key)
    return Response(
        content=data,
        media_type="chemical/x-pdb",
        headers={"Content-Disposition": f"attachment; filename=structure_{job_id}.pdb"},
    )


@router.get("/{job_id}/plddt")
async def get_plddt(job_id: str) -> dict:
    """Return pLDDT confidence scores for the frontend visualisation."""
    key = f"{job_id}/plddt.json"
    if not file_exists("structures", key):
        raise HTTPException(status_code=404, detail="pLDDT data not found")

    import json
    data = download_file("structures", key)
    return json.loads(data)
