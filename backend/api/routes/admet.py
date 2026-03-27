import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from models.schemas import AdmetRequest, AdmetResponse, AdmetInput
from modules.admet import AdmetModule

router = APIRouter()


@router.post("/predict")
async def predict_admet(
    request: AdmetRequest,
    db: AsyncSession = Depends(get_session),
):
    """Run ADMET prediction.

    Tier 1 (RDKit) runs synchronously and returns immediately.
    Tier 2 (SwissADME) would dispatch a background job if enabled.
    """
    if len(request.smiles_list) > 10000:
        raise HTTPException(status_code=422, detail="Maximum 10000 SMILES per request")

    job_id = str(uuid.uuid4())

    # Tier 1 runs synchronously — fast enough for thousands of molecules
    module = AdmetModule()
    module_input = AdmetInput(
        job_id=job_id,
        smiles_list=request.smiles_list,
        run_tier2=False,
    )
    result = module.execute(module_input)

    if result.status == "failed":
        raise HTTPException(status_code=422, detail=result.errors)

    return {
        "job_id": job_id,
        "status": "completed",
        **result.data,
    }
