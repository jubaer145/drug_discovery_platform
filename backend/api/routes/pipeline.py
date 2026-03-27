from fastapi import APIRouter, Depends, HTTPException
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
    # Validate: at least one target specification
    has_target = any([
        request.target_pdb_path,
        request.target_pdb_id,
        request.target_uniprot_id,
        request.target_sequence,
    ])
    if not has_target:
        raise HTTPException(
            status_code=422,
            detail="At least one target specification required (pdb_id, uniprot_id, sequence, or pdb_path)",
        )

    # Validate: virtual screening needs molecules
    if request.task_type == "virtual_screening":
        if request.molecules is None or (
            not request.molecules.smiles
            and not request.molecules.sdf_base64
            and not request.molecules.use_zinc_subset
        ):
            raise HTTPException(
                status_code=422,
                detail="Virtual screening requires molecules (smiles, sdf_base64, or use_zinc_subset)",
            )

    return await dispatch_pipeline(request, db)
