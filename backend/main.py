import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
from core.websocket import manager, subscribe_to_job_progress
from api.routes import ai_query, targets, structures, design, molecules, docking, admet, pipeline, jobs

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create MinIO buckets
    try:
        from core.storage import ensure_buckets
        ensure_buckets()
    except Exception:
        pass  # MinIO may not be available in test environment
    yield
    await engine.dispose()


app = FastAPI(
    title="Drug Discovery Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_query.router,   prefix="/api/ai",         tags=["AI Query"])
app.include_router(targets.router,    prefix="/api/targets",    tags=["Targets"])
app.include_router(structures.router, prefix="/api/structures", tags=["Structures"])
app.include_router(design.router,     prefix="/api/design",     tags=["Design"])
app.include_router(molecules.router,  prefix="/api/molecules",  tags=["Molecules"])
app.include_router(docking.router,    prefix="/api/docking",    tags=["Docking"])
app.include_router(admet.router,      prefix="/api/admet",      tags=["ADMET"])
app.include_router(pipeline.router,   prefix="/api/pipeline",   tags=["Pipeline"])
app.include_router(jobs.router,       prefix="/api/jobs",       tags=["Jobs"])


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/files/{bucket}/{path:path}")
async def download_file_endpoint(bucket: str, path: str):
    """Generic file download from MinIO storage."""
    from fastapi.responses import Response
    from core.storage import download_file, file_exists
    if not file_exists(bucket, path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    data = download_file(bucket, path)
    content_type = "application/octet-stream"
    if path.endswith(".pdb"):
        content_type = "chemical/x-pdb"
    elif path.endswith(".json"):
        content_type = "application/json"
    elif path.endswith(".sdf"):
        content_type = "chemical/x-mdl-sdfile"
    return Response(content=data, media_type=content_type)


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    # Start Redis subscriber in background to forward progress updates
    sub_task = asyncio.create_task(subscribe_to_job_progress(job_id, websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        sub_task.cancel()
        manager.disconnect(job_id, websocket)
