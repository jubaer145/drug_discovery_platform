import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.queue import run_target_lookup
from models.schemas import TargetLookupRequest, TargetLookupResponse

router = APIRouter()


@router.post("/lookup", response_model=TargetLookupResponse)
async def lookup_target(
    request: TargetLookupRequest,
    db: AsyncSession = Depends(get_session),
) -> TargetLookupResponse:
    """Dispatch target lookup as a background job."""
    job_id = str(uuid.uuid4())
    run_target_lookup.delay(job_id, request.query, request.user_id)
    return TargetLookupResponse(job_id=job_id, status="pending")


@router.get("/search")
async def search_targets(
    q: str = Query(..., min_length=1, description="Protein name, gene, or disease"),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[dict]:
    """Synchronous autocomplete search via UniProt text search."""
    import httpx
    from core.config import settings

    url = f"{settings.uniprot_api_url}/search"
    params = {
        "query": f"{q} AND reviewed:true AND organism_id:9606",
        "format": "json",
        "size": str(limit),
        "fields": "accession,protein_name,gene_names,organism_name",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        raise HTTPException(status_code=502, detail=f"UniProt search failed: {e}")

    return [
        {
            "uniprot_id": r.get("primaryAccession", ""),
            "protein_name": (
                r.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value", "")
            ),
            "gene_symbol": (
                r.get("genes", [{}])[0].get("geneName", {}).get("value", "")
                if r.get("genes") else ""
            ),
            "organism": r.get("organism", {}).get("scientificName", ""),
        }
        for r in results
    ]
