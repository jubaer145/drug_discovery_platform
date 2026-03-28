import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from models.database import Job
from models.schemas import JobRead

router = APIRouter()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_session),
) -> JobRead:
    """Fetch job status and results by job_id."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid job ID format")

    result = await db.execute(select(Job).where(Job.id == uid))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # If job is still pending/running, check Redis for cached result from Celery
    if job.status in ("pending", "running"):
        import json
        import redis
        from core.config import settings
        try:
            r = redis.Redis.from_url(settings.redis_url)
            cached = r.get(f"job_result:{job_id}")
            if cached:
                data = json.loads(cached)
                job.status = data["status"]
                job.output_data = data.get("output_data")
                job.error = data.get("error")
                await db.commit()
        except Exception:
            pass

    return job


@router.get("/")
async def list_jobs(
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """List jobs with optional filtering and pagination."""
    query = select(Job).order_by(Job.created_at.desc())

    if user_id:
        query = query.where(Job.user_id == user_id)
    if status:
        query = query.where(Job.status == status)
    if job_type:
        query = query.where(Job.job_type == job_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [JobRead.model_validate(j).model_dump() for j in jobs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Cancel a running job by revoking its Celery task."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid job ID format")

    result = await db.execute(select(Job).where(Job.id == uid))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status in ("completed", "failed", "cancelled"):
        return {"job_id": job_id, "status": job.status, "message": "Job already finished"}

    # Revoke the Celery task
    from core.queue import celery_app
    celery_app.control.revoke(job_id, terminate=True)

    # Update status in DB
    job.status = "cancelled"
    await db.commit()

    return {"job_id": job_id, "status": "cancelled"}
