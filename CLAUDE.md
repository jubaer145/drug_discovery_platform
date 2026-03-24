# Drug Discovery Platform — CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

If you're not sure about any section, or if some information in the prompt is incomplete, you must ask me. 

## What this project is
End-to-end drug discovery simulation platform. Two user types:
- Technical: know protein names, PDB IDs → direct pipeline access
- Non-technical: know the disease → AI translates to molecular targets

## Commands

```bash
# Start all services
docker compose up

# Backend dev (from backend/)
uvicorn main:app --reload

# Run all backend tests
pytest backend/tests/

# Run a single test file
pytest backend/tests/test_docking.py -v

# Frontend dev (from frontend/)
npm run dev

# Frontend lint + type-check
npm run build
```

## Architecture rules — never violate these

1. ALL pipeline modules inherit from backend/modules/base.py BaseModule
2. ALL compute-heavy operations are Celery tasks — never block a route handler
3. ALL route handlers return job_id immediately — never wait for computation
4. ALL inputs/outputs use Pydantic models — no raw dicts crossing API boundary
5. ALL modules have tests in backend/tests/ before moving to next sprint
6. The AI query module calls Anthropic API — always use claude-sonnet-4-6
7. Never store binary files (PDB, SDF) in PostgreSQL — use MinIO/S3

## Tech stack

Backend:
- FastAPI + Python 3.11
- Celery + Redis (task queue)
- PostgreSQL + SQLAlchemy async (data)
- MinIO (file storage — S3-compatible, runs locally in Docker)
- httpx (async HTTP — never use requests)
- RDKit (chemistry)
- Anthropic Python SDK (AI query module)

Frontend:
- Next.js 14 (App Router)
- TypeScript (strict mode)
- Tailwind CSS
- 3Dmol.js (protein visualisation, load from CDN)

## File format conventions
- Protein structures: PDB format at /data/structures/{job_id}.pdb
- Molecules input: SMILES strings in DB, SDF files at /data/molecules/{job_id}.sdf
- Job results: JSON in PostgreSQL + raw files at /data/results/{job_id}/
- All file paths are relative to /data/ — never hardcode absolute paths

## Environment variables (all in core/config.py)
ANTHROPIC_API_KEY, DATABASE_URL, REDIS_URL, MINIO_ENDPOINT,
MINIO_ACCESS_KEY, MINIO_SECRET_KEY, ESMFOLD_API_URL,
ALPHAFOLD_DB_URL, PDB_API_URL, UNIPROT_API_URL

## Job status values (use exactly these strings)
pending → running → completed | failed

## Do NOT
- Do not make synchronous HTTP calls inside async route handlers
- Do not mix binding / functional / ADMET assay types without labeling assay_type
- Do not hardcode any URL — all external URLs come from config.py
- Do not import from modules/ directly in routes/ — routes call core/pipeline.py
- Do not modify base.py after Sprint 0 — it is the contract all modules honour