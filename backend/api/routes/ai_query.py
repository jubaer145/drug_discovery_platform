import uuid

from fastapi import APIRouter, HTTPException

from models.schemas import AIQueryInput, AIQueryRequest, AIQueryResponse
from modules.ai_query import AIQueryModule

router = APIRouter()

_module = AIQueryModule()


@router.post("/suggest-targets", response_model=AIQueryResponse)
def suggest_targets(request: AIQueryRequest) -> AIQueryResponse:
    """Call Claude to suggest drug targets from a natural-language query.

    This route is synchronous — the Claude API call is fast enough (~2s)
    that we return the result directly instead of creating a background job.
    """
    job_id = str(uuid.uuid4())

    module_input = AIQueryInput(
        job_id=job_id,
        user_id=request.user_id,
        query=request.query,
        max_targets=request.max_targets,
    )

    result = _module.execute(module_input)

    if result.status == "failed":
        raise HTTPException(status_code=422, detail=result.errors)

    return AIQueryResponse(**result.data)
