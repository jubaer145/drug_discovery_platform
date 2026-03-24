# Drug Discovery Platform — Complete System Plan & Claude Code Prompts

> **How to use this document:**  
> Open Claude Code in your project folder. Work through each sprint in order.  
> Copy the prompt under each sprint header exactly into Claude Code.  
> Do not start a new sprint until the previous one passes its tests.

---

## 1. What We're Building

An end-to-end drug discovery simulation platform with two types of users:

- **Technical users** (researchers, computational biologists) — know protein names, PDB IDs, want direct access to the pipeline
- **Non-technical users** (medical students, disease advocates, enthusiasts) — know the disease and clinical picture, need AI to translate that into molecular targets

Both users go through the same pipeline. The difference is only at Step 1 — how they find their target.

### The six-step user journey

```
Step 1: Find target    → technical search OR natural language AI query
Step 2: Choose task    → virtual screening / protein design / de novo generation
Step 3: Structure      → auto-fetch from PDB or predict with ESMFold
Step 4: Run pipeline   → docking + ADMET run async in background
Step 5: Results        → ranked candidates with binding scores + ADMET flags
Step 6: 3D inspection  → protein + ligand visualised in 3Dmol.js
```

---

## 2. Final Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 14 + TypeScript + Tailwind                  │
│  Step wizard · 3Dmol.js viewer · Molecule sketcher · Dashboard  │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│  API Gateway — FastAPI + Python 3.11                            │
│  Auth · Rate limiting · CORS · Job routing                      │
└──┬──────────┬──────────┬───────────┬────────────┬──────────────┘
   │          │          │           │            │
┌──▼──┐  ┌───▼──┐  ┌────▼───┐  ┌───▼────┐  ┌───▼──────┐
│ AI  │  │Target│  │Struct. │  │Docking │  │  ADMET   │
│Query│  │Lookup│  │Predict │  │Module  │  │  Module  │
│     │  │      │  │        │  │        │  │          │
│Claude  │PDB   │  │ESMFold │  │AutoDock│  │RDKit +   │
│API  │  │UniProt  │AlphaFold  │Vina    │  │SwissADME │
└──┬──┘  └───┬──┘  └────┬───┘  └───┬────┘  └───┬──────┘
   │          │          │           │            │
┌──▼──────────▼──────────▼───────────▼────────────▼──────────────┐
│  Job Queue — Celery + Redis                                     │
│  Async task execution · GPU dispatch · Progress streaming       │
└─────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Storage                                                        │
│  PostgreSQL (jobs, results, users) · Redis (queue, cache)       │
│  MinIO / S3 (PDB files, SDF, results) · Chroma (embeddings)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Project File Structure

Tell Claude Code to create this exact structure in Sprint 0.

```
drug-discovery-platform/
│
├── CLAUDE.md                          ← Claude Code reads this every session
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── main.py                        ← FastAPI app entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                    ← shared dependencies (db, auth)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── ai_query.py            ← POST /api/ai/suggest-targets
│   │       ├── targets.py             ← POST /api/targets/lookup
│   │       ├── structures.py          ← POST /api/structures/predict
│   │       ├── design.py              ← POST /api/design/protein
│   │       ├── molecules.py           ← POST /api/molecules/generate
│   │       ├── docking.py             ← POST /api/docking/run
│   │       ├── admet.py               ← POST /api/admet/predict
│   │       ├── pipeline.py            ← POST /api/pipeline/run
│   │       └── jobs.py                ← GET  /api/jobs/{job_id}
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  ← all env vars in one place
│   │   ├── database.py                ← SQLAlchemy async setup
│   │   ├── queue.py                   ← Celery app + all task definitions
│   │   ├── pipeline.py                ← pipeline orchestrator
│   │   └── websocket.py               ← WebSocket manager
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py                    ← BaseModule abstract class (DO NOT MODIFY)
│   │   ├── ai_query.py                ← Claude API target suggestion
│   │   ├── target_lookup.py           ← PDB + UniProt fetching
│   │   ├── structure_pred.py          ← ESMFold API wrapper
│   │   ├── protein_design.py          ← RFdiffusion wrapper
│   │   ├── mol_generation.py          ← REINVENT wrapper
│   │   ├── docking.py                 ← AutoDock Vina wrapper
│   │   └── admet.py                   ← RDKit + SwissADME wrapper
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py                ← SQLAlchemy ORM models
│   │   └── schemas.py                 ← Pydantic request/response schemas
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_ai_query.py
│       ├── test_target_lookup.py
│       ├── test_structure_pred.py
│       ├── test_docking.py
│       └── test_admet.py
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    ├── Dockerfile
    │
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                   ← landing / pipeline wizard
    │   ├── jobs/
    │   │   └── [id]/
    │   │       └── page.tsx           ← results + 3D viewer
    │   └── library/
    │       └── page.tsx               ← saved molecules + history
    │
    ├── components/
    │   ├── pipeline/
    │   │   ├── PipelineWizard.tsx     ← top-level step manager
    │   │   ├── Step1Target.tsx        ← dual-mode target entry
    │   │   ├── Step2Task.tsx          ← task selection cards
    │   │   ├── Step3Structure.tsx     ← structure preview
    │   │   ├── Step4Running.tsx       ← live job progress
    │   │   ├── Step5Results.tsx       ← ranked candidates table
    │   │   └── Step6Viewer.tsx        ← 3Dmol.js 3D viewer
    │   ├── target/
    │   │   ├── TechnicalSearch.tsx    ← PDB/UniProt search input
    │   │   ├── NaturalLanguageQuery.tsx ← AI-powered query bar
    │   │   ├── TargetSuggestionCard.tsx ← individual AI suggestion
    │   │   └── ProteinInfoCard.tsx    ← resolved target display
    │   ├── molecule/
    │   │   ├── SmilesInput.tsx        ← paste/upload molecules
    │   │   └── MoleculeCard.tsx       ← individual molecule result
    │   ├── viewer/
    │   │   └── StructureViewer.tsx    ← 3Dmol.js wrapper component
    │   └── ui/
    │       ├── JobProgressBar.tsx
    │       ├── AdmetBadge.tsx
    │       └── ConfidencePill.tsx
    │
    ├── lib/
    │   ├── api.ts                     ← typed API client
    │   ├── types.ts                   ← all shared TypeScript types
    │   └── websocket.ts               ← WebSocket hook
    │
    └── hooks/
        ├── useJob.ts                  ← poll job status
        └── usePipeline.ts             ← pipeline state machine
```

---

## 4. CLAUDE.md

**Create this file in your project root before anything else.**  
Claude Code reads it automatically at the start of every session.

```markdown
# Drug Discovery Platform — CLAUDE.md

## What this project is
End-to-end drug discovery simulation platform. Two user types:
- Technical: know protein names, PDB IDs → direct pipeline access
- Non-technical: know the disease → AI translates to molecular targets

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
```

---

## 5. Base Module Contract

**This is the most important file. Write it once, never touch it again.**  
Every pipeline module inherits from this. It enforces validate → run → output.

```python
# backend/modules/base.py

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ModuleInput(BaseModel):
    job_id: str
    user_id: str | None = None


class ModuleOutput(BaseModel):
    job_id: str
    status: str          # "completed" | "failed"
    data: dict[str, Any]
    errors: list[str] = []
    warnings: list[str] = []


class BaseModule(ABC):
    """
    Contract for all pipeline modules.
    
    Subclasses implement validate_input() and run().
    Never override execute() — it handles logging and error wrapping.
    
    Usage:
        module = TargetLookupModule()
        result = module.execute(TargetLookupInput(job_id="abc", query="EGFR"))
    """

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        """
        Returns (is_valid, error_message).
        Override to add input-specific validation.
        """
        return True, ""

    @abstractmethod
    def run(self, input: ModuleInput) -> ModuleOutput:
        """Core logic. Only called if validate_input passes."""
        pass

    def execute(self, input: ModuleInput) -> ModuleOutput:
        logger.info(f"[{self.__class__.__name__}] Starting job {input.job_id}")
        try:
            is_valid, error_msg = self.validate_input(input)
            if not is_valid:
                logger.warning(f"[{self.__class__.__name__}] Validation failed: {error_msg}")
                return ModuleOutput(
                    job_id=input.job_id,
                    status="failed",
                    data={},
                    errors=[error_msg]
                )
            result = self.run(input)
            logger.info(f"[{self.__class__.__name__}] Completed job {input.job_id} — status: {result.status}")
            return result
        except Exception as e:
            logger.exception(f"[{self.__class__.__name__}] Unhandled error in job {input.job_id}")
            return ModuleOutput(
                job_id=input.job_id,
                status="failed",
                data={},
                errors=[f"Unhandled exception: {str(e)}"]
            )
```

---

## 6. Sprint Prompts for Claude Code

---

### SPRINT 0 — Scaffold

> **Goal:** Full project skeleton, Docker, database, base module.  
> **Time:** ~2 hours  
> **Done when:** `docker compose up` starts all services with no errors.

---

**Prompt:**

```
I'm building an end-to-end drug discovery simulation platform.

Read the project structure below and create every file and directory listed.
Do not implement any drug discovery logic yet — only infrastructure.

PROJECT STRUCTURE:
[paste the entire directory tree from Section 3 above]

TASKS:

1. Create docker-compose.yml with these services:
   - backend: FastAPI on port 8000, volume mount ./backend:/app
   - frontend: Next.js on port 3000, volume mount ./frontend:/app
   - postgres: PostgreSQL 15, database=drugdiscovery, user=admin, password=secret
   - redis: Redis 7
   - minio: MinIO (S3-compatible), ports 9000 and 9001, 
     user=minioadmin, password=minioadmin
   - celery_worker: same image as backend, command: celery -A core.queue worker
   - celery_flower: Flower monitoring on port 5555
   All services on network: drug-discovery-net

2. Create .env.example with all variables from CLAUDE.md environment section,
   plus: POSTGRES_URL=postgresql+asyncpg://admin:secret@postgres:5432/drugdiscovery
   REDIS_URL=redis://redis:6379/0

3. Create backend/core/config.py:
   Use pydantic-settings BaseSettings. Load all env vars.
   Export a single `settings` instance.

4. Create backend/core/database.py:
   Async SQLAlchemy engine + session factory.
   Export: engine, async_session, get_db (FastAPI dependency).

5. Create backend/models/database.py with these ORM models:
   - Job: id (uuid), user_id (str, nullable), status (str), 
     job_type (str), input_data (JSON), output_data (JSON, nullable),
     error (str, nullable), created_at, updated_at
   - SavedTarget: id (uuid), user_id (str), pdb_id (str), 
     protein_name (str), metadata (JSON), created_at
   - SavedMolecule: id (uuid), user_id (str), smiles (str), 
     name (str), job_id (uuid FK), scores (JSON), created_at

6. Create backend/models/schemas.py with Pydantic models for:
   - JobCreate, JobRead, JobStatusUpdate
   - TargetLookupRequest, TargetLookupResponse
   - AIQueryRequest, AIQueryResponse, TargetSuggestion
   - StructurePredictRequest, StructurePredictResponse
   - DockingRequest, DockingResponse, DockingResult
   - AdmetRequest, AdmetResponse, AdmetProfile
   - PipelineRequest, PipelineResponse
   - MoleculeInput (accepts smiles list or sdf_base64 or use_zinc_subset bool)

7. Create backend/modules/base.py with the exact code from Section 5 of the spec.

8. Create backend/core/queue.py:
   Celery app connected to Redis. Import placeholder tasks 
   (they will be filled in each sprint). Export: celery_app.

9. Create backend/main.py:
   FastAPI app with CORS (allow all origins for now), lifespan that 
   creates DB tables on startup. Register all routers from api/routes/.
   Health check endpoint GET /health returns {"status": "ok", "version": "0.1.0"}.

10. Create frontend/ as a Next.js 14 app with TypeScript and Tailwind:
    - app/layout.tsx: root layout, dark/light theme support
    - app/page.tsx: placeholder "Drug Discovery Platform — coming soon"
    - lib/types.ts: TypeScript interfaces matching all backend Pydantic schemas
    - lib/api.ts: typed fetch wrapper for all backend endpoints

11. Create backend/requirements.txt:
    fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic,
    celery[redis], redis, httpx, pydantic-settings, python-multipart,
    rdkit, anthropic, minio, flower

12. Create frontend/package.json with: next, react, react-dom, typescript,
    tailwindcss, @types/react, @types/node

Write a README.md explaining how to start the project with docker compose up --build.

After creating all files, verify by listing the complete directory tree.
```

---

### SPRINT 1 — AI Query Module (Natural Language Target Finder)

> **Goal:** The "plain language" panel from Step 1 of the UI.  
> **Time:** 1 day  
> **Done when:** POST /api/ai/suggest-targets with "what causes Alzheimer's" returns 4 structured target suggestions with confidence scores.

---

**Prompt:**

```
Context — read these files before starting:
- backend/modules/base.py
- backend/models/schemas.py
- backend/core/config.py

Implement the AI Query module. This is the brain of the natural language 
target entry panel — it takes a plain-language disease/condition question 
from a non-technical user and returns structured drug target suggestions.

FILE: backend/modules/ai_query.py

The module calls the Anthropic API with claude-sonnet-4-6.
It inherits from BaseModule.

Input schema (add to schemas.py):
  AIQueryInput(ModuleInput):
    query: str          # the user's natural language question
    max_targets: int = 5

Output data format (list of TargetSuggestion):
  {
    "targets": [
      {
        "protein_name": "BACE1",
        "gene_symbol": "BACE1",
        "uniprot_id": "P56817",
        "full_name": "Beta-secretase 1",
        "confidence": "high",     # "high" | "medium" | "low"
        "mechanism_summary": "2-sentence clinical explanation of why relevant",
        "druggability_note": "1 sentence on pocket quality / tractability",
        "tags": ["amyloid pathway", "crystal structure available"],
        "has_pdb_structure": true,
        "clinical_stage": "phase3_trials",  # or "preclinical" | "approved" | "unknown"
        "difficulty": "moderate"  # "easy" | "moderate" | "difficult"
      }
    ],
    "query_interpretation": "1 sentence summarising what disease/mechanism was detected",
    "confidence_explanation": "1 sentence on overall evidence quality"
  }

The Anthropic API system prompt must:
- Establish the AI as a drug discovery expert and medicinal chemist
- Instruct it to prioritise targets with: (a) validated 3D structures in PDB,
  (b) known druggable pockets, (c) published clinical or preclinical evidence
- Tell it to be honest about difficulty (e.g. APOE4 is "difficult")
- Tell it to explain mechanisms in terms a medical student would understand
- Tell it to respond ONLY in valid JSON matching the output schema above
- Tell it NOT to include markdown fences or any text outside the JSON

Validation rules (in validate_input):
- query must be between 10 and 500 characters
- query must not be only numbers or symbols
- max_targets must be between 1 and 8

FILE: backend/api/routes/ai_query.py

Route: POST /api/ai/suggest-targets
- Accepts AIQueryRequest (query: str, max_targets: int = 5)
- This route IS synchronous (fast enough — Claude API ~2s)
- Does NOT create a job — returns directly
- Returns AIQueryResponse with list of TargetSuggestion

FILE: backend/tests/test_ai_query.py

Write 4 tests:
1. test_alzheimers_query: "what proteins drive Alzheimer's disease?" 
   → assert response has 3-5 targets, all have confidence field, 
   at least one target has "high" confidence
2. test_cancer_query: "what causes triple-negative breast cancer resistance?"
   → assert response has targets, all have uniprot_id set
3. test_short_query_fails: "hi" → assert validation fails with clear error
4. test_response_structure: any valid query → assert all required fields present
   in every returned target

Important: use pytest-asyncio. Mock the Anthropic client in tests 
using unittest.mock so tests don't require a real API key.
```

---

### SPRINT 2 — Target Lookup Module

> **Goal:** Given a protein name, PDB ID, or UniProt accession, fetch complete target info.  
> **Time:** 1 day  
> **Done when:** Lookup of "EGFR", "P00533", and "1IEP" all return structured protein cards.

---

**Prompt:**

```
Context — read these files before starting:
- backend/modules/base.py
- backend/models/schemas.py  
- backend/modules/ai_query.py  (to understand the pattern)

Implement the Target Lookup module.

FILE: backend/modules/target_lookup.py

Input schema (add to schemas.py):
  TargetLookupInput(ModuleInput):
    query: str          # PDB ID | UniProt accession | protein name | disease
    query_type: str = "auto"   # "pdb_id" | "uniprot" | "name" | "auto"

Logic:
  1. If query_type is "auto", detect type:
     - 4-character alphanumeric → PDB ID (e.g. "1IEP", "6LU7")
     - 6-10 char with numbers → UniProt accession (e.g. "P00533")
     - Otherwise → protein/disease name search
  
  2. PDB ID lookup:
     GET https://data.rcsb.org/rest/v1/core/entry/{pdb_id}
     GET https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/1
     Extract: title, organism, resolution, method (X-ray/cryo-EM/NMR),
     deposition date, all UniProt accessions linked

  3. UniProt accession lookup:
     GET https://rest.uniprot.org/uniprotkb/{accession}.json
     Extract: protein name, gene name, organism, sequence length,
     sequence (FASTA), function description, disease associations,
     subcellular location, all linked PDB IDs

  4. Name search:
     First try UniProt text search:
     GET https://rest.uniprot.org/uniprotkb/search?query={name}&format=json&size=5
     Return top 5 candidates for the user to choose from.
     If name looks like a disease, also note this for the AI Query module.

  5. After resolving the target, always:
     - Fetch the list of all PDB structures from RCSB for that UniProt:
       GET https://www.rcsb.org/search/api/... (use RCSB search API)
     - Count total structures, identify best (highest resolution X-ray)
     - Check if AlphaFold structure exists:
       HEAD https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb

Output data format:
  {
    "protein_name": "Epidermal growth factor receptor",
    "gene_symbol": "EGFR",
    "uniprot_id": "P00533",
    "organism": "Homo sapiens",
    "sequence_length": 1210,
    "sequence": "MRPSGTAGAALLALLAALCPASRALEEKKVC...",
    "function_summary": "Receptor tyrosine kinase...",
    "disease_associations": ["lung adenocarcinoma", "glioblastoma"],
    "pdb_structures": [
      {"pdb_id": "7L9H", "resolution": 2.3, "method": "X-ray", 
       "has_ligand": true, "ligand_name": "Osimertinib"}
    ],
    "best_pdb_id": "7L9H",
    "total_pdb_count": 285,
    "has_alphafold": true,
    "alphafold_url": "https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v4.pdb",
    "multiple_candidates": null   # or list of candidates if name search returned many
  }

All HTTP calls must use httpx with timeout=30s.
Handle 404 gracefully — return partial data with a warning, not an error.

FILE: backend/api/routes/targets.py

Route: POST /api/targets/lookup
- Accepts TargetLookupRequest
- Creates Job record in DB with job_type="target_lookup"
- Dispatches Celery task: lookup_target_task
- Returns {job_id} immediately

Route: GET /api/targets/search?q={query}&limit=5
- Synchronous, fast (just hits UniProt search)
- Used by frontend autocomplete — must respond in <500ms
- Returns list of {uniprot_id, protein_name, gene_symbol, organism}

FILE: backend/core/queue.py — add:
  @celery_app.task(bind=True, max_retries=2)
  def lookup_target_task(self, job_id: str, input_data: dict): ...

FILE: backend/tests/test_target_lookup.py

Tests:
1. test_pdb_id_lookup: query="1IEP" → protein_name contains "ABL", has pdb_structures
2. test_uniprot_lookup: query="P00533" → gene_symbol="EGFR", sequence_length=1210
3. test_name_lookup: query="EGFR" → resolves correctly, has uniprot_id
4. test_invalid_pdb: query="ZZZZ" → status="failed", clear error message
5. test_alphafold_check: query="P00533" → has_alphafold=true
```

---

### SPRINT 3 — Structure Prediction Module

> **Goal:** Given a protein sequence, predict 3D structure via ESMFold API.  
> **Time:** 1 day  
> **Done when:** A FASTA sequence returns a PDB file with pLDDT confidence scores.

---

**Prompt:**

```
Context — read these files before starting:
- backend/modules/base.py
- backend/modules/target_lookup.py
- backend/core/queue.py

Implement the Structure Prediction module.

This module is used when:
  (a) A target has no experimental PDB structure
  (b) The user wants a predicted structure for a custom sequence

FILE: backend/modules/structure_pred.py

Input schema:
  StructurePredInput(ModuleInput):
    sequence: str              # amino acid sequence (single-letter, no spaces)
    sequence_name: str = ""    # optional label
    force_predict: bool = False # predict even if PDB exists

Validation:
  - Sequence length: 10 to 400 AA (ESMFold API hard limit is 400)
  - Only valid AA characters: ACDEFGHIKLMNPQRSTVWY (plus X for unknown)
  - Strip whitespace and newlines before validation

ESMFold API call:
  POST https://api.esmatlas.com/foldSequence/v1/pdb/
  Content-Type: application/x-www-form-urlencoded
  Body: the raw amino acid sequence string
  Returns: PDB format string

After receiving PDB:
  1. Parse the B-factor column (column 61-66 in ATOM records) 
     to extract per-residue pLDDT confidence scores
  2. Calculate: mean_plddt, min_plddt, pct_high_confidence (pLDDT > 70)
  3. Save PDB to MinIO: structures/{job_id}/predicted.pdb
  4. Save confidence JSON to MinIO: structures/{job_id}/plddt.json

Output data:
  {
    "pdb_url": "structures/{job_id}/predicted.pdb",
    "plddt_url": "structures/{job_id}/plddt.json",
    "mean_plddt": 82.4,
    "min_plddt": 45.2,
    "pct_high_confidence": 0.87,
    "sequence_length": 380,
    "prediction_source": "ESMFold",
    "quality_assessment": "high"  # "high" (>80) | "medium" (60-80) | "low" (<60)
  }

MinIO helper: create backend/core/storage.py with:
  - upload_file(bucket, key, data: bytes) -> str (URL)
  - download_file(bucket, key) -> bytes
  - file_exists(bucket, key) -> bool
  Bucket names: "structures", "molecules", "results"
  Auto-create buckets on startup if they don't exist.

FILE: backend/api/routes/structures.py

Route: POST /api/structures/predict
  - Validates sequence server-side (not just Pydantic — custom logic)
  - Creates Job, dispatches predict_structure_task
  - Returns {job_id}

Route: GET /api/structures/{job_id}/download
  - Streams the PDB file from MinIO
  - Sets Content-Disposition: attachment; filename=structure.pdb

Route: GET /api/structures/{job_id}/plddt
  - Returns the pLDDT JSON for the frontend confidence visualisation

Add to backend/core/queue.py:
  @celery_app.task(bind=True, max_retries=1, time_limit=300)
  def predict_structure_task(self, job_id: str, input_data: dict): ...
  (ESMFold can take up to 5 minutes for long sequences)

FILE: backend/tests/test_structure_pred.py

Tests (mock the ESMFold API — don't make real calls):
1. test_valid_sequence: short valid sequence → status completed, has pdb_url
2. test_sequence_too_long: 401 AA sequence → validation fails
3. test_invalid_characters: sequence with "B" and "Z" → validation fails
4. test_plddt_parsing: given a mock PDB string with known B-factors 
   → assert mean_plddt calculated correctly
5. test_quality_assessment: mock plddt=85 → quality="high"
```

---

### SPRINT 4 — Docking Module

> **Goal:** Given a PDB structure and a list of SMILES, run AutoDock Vina and return scored poses.  
> **Time:** 3-4 days (most complex module)  
> **Done when:** 10 SMILES docked against EGFR return binding affinities in kcal/mol.

---

**Prompt:**

```
Context — read these files before starting:
- backend/modules/base.py
- backend/core/storage.py
- backend/models/schemas.py

Implement the Docking module. This wraps AutoDock Vina.

Assume these are installed in the Docker container:
  /usr/bin/vina         (AutoDock Vina 1.2)
  /usr/bin/obabel       (OpenBabel for format conversion)
  /usr/bin/fpocket      (pocket detection)
  /usr/bin/prepare_receptor  (MGLTools receptor prep script)

FILE: backend/modules/docking.py

Input schema:
  DockingInput(ModuleInput):
    pdb_path: str             # MinIO path to receptor PDB
    smiles_list: list[str]    # ligands to dock, max 10000
    binding_site: dict | None = None  
      # {"center_x": float, "center_y": float, "center_z": float,
      #  "size_x": 20, "size_y": 20, "size_z": 20}
    exhaustiveness: int = 8   # Vina exhaustiveness (8=default, 32=thorough)
    num_poses: int = 3        # poses per ligand to return

Pipeline for each ligand:
  Step A — Pocket detection (if binding_site is None):
    Run fpocket on the PDB: subprocess ["fpocket", "-f", receptor.pdb]
    Parse fpocket output to extract top pocket:
    - druggability score > 0.5
    - volume > 200 Ų
    If no druggable pocket found: fail with clear message

  Step B — Receptor preparation:
    Convert PDB to PDBQT:
    subprocess: obabel receptor.pdb -O receptor.pdbqt -xr
    (removes waters, adds charges)

  Step C — Per-ligand docking (run in parallel using concurrent.futures):
    For each SMILES:
    1. Validate SMILES with RDKit: Chem.MolFromSmiles(smiles)
       Skip invalid SMILES with a warning (don't fail whole batch)
    2. Generate 3D conformer:
       from rdkit.Chem import AllChem
       mol = Chem.AddHs(mol)
       AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
       AllChem.MMFFOptimizeMolecule(mol)
    3. Convert to PDBQT: 
       Write SDF, then: obabel ligand.sdf -O ligand.pdbqt
    4. Run Vina:
       subprocess: vina --receptor receptor.pdbqt --ligand ligand.pdbqt
         --center_x X --center_y Y --center_z Z
         --size_x SX --size_y SY --size_z SZ
         --exhaustiveness {exhaustiveness} --num_modes {num_poses}
         --out poses.pdbqt --log vina.log
    5. Parse vina.log: extract affinity (kcal/mol) for each pose
    6. If docking fails for this ligand: record error, continue with next

  Step D — Aggregate and sort:
    Sort all successfully docked ligands by best pose affinity (most negative first)
    Apply basic filters: affinity < -4.0 kcal/mol (remove trivial non-binders)

Output data:
  {
    "docked_count": 8,
    "failed_count": 2,
    "failed_smiles": ["invalid_smiles_here"],
    "binding_site_used": {"center_x": ..., ...},
    "pocket_detected_automatically": true,
    "results": [
      {
        "smiles": "CC1=C2...",
        "rank": 1,
        "best_affinity_kcal_mol": -9.2,
        "all_pose_affinities": [-9.2, -8.8, -8.1],
        "pose_pdbqt_path": "results/{job_id}/pose_1.pdbqt",
        "docking_success": true
      }
    ]
  }

Use concurrent.futures.ThreadPoolExecutor(max_workers=4) for parallel docking.
All temp files go to /tmp/docking/{job_id}/ — clean up after completion.
Save final pose files to MinIO: results/{job_id}/

FILE: backend/api/routes/docking.py

Route: POST /api/docking/run
  - Accepts DockingRequest 
    (pdb_job_id OR pdb_minio_path, smiles_list OR sdf_base64, optional binding_site)
  - Resolves the PDB path from the previous job's output
  - Creates Job, dispatches dock_molecules_task
  - Returns {job_id, estimated_minutes: int}

Add to backend/core/queue.py:
  @celery_app.task(bind=True, max_retries=0, time_limit=3600)
  def dock_molecules_task(self, job_id: str, input_data: dict): ...
  (No retry for docking — it's idempotent but expensive)

Progress updates during docking:
  After each ligand completes, update job in DB:
  {"step": "docking", "completed": N, "total": M, "current_smiles": "..."}
  This powers the frontend progress bar.

FILE: backend/tests/test_docking.py

Tests (mock all subprocess calls):
1. test_smiles_validation: invalid SMILES in list → skipped with warning, 
   valid ones proceed
2. test_pocket_detection: mock fpocket output → binding_site parsed correctly
3. test_vina_output_parsing: mock vina.log with known affinities → 
   results sorted correctly
4. test_all_fail: all SMILES invalid → status failed, clear error
5. test_partial_fail: 8/10 succeed → docked_count=8, failed_count=2
```

---

### SPRINT 5 — ADMET Module

> **Goal:** Given SMILES strings, predict drug-likeness, ADMET properties, and toxicity flags.  
> **Time:** 1-2 days  
> **Done when:** 10 molecules return traffic-light ADMET profiles with pass/fail flags.

---

**Prompt:**

```
Context — read these files before starting:
- backend/modules/base.py
- backend/models/schemas.py

Implement the ADMET prediction module. Two-tier approach:
Tier 1 is instant (RDKit, no network). Tier 2 is external (SwissADME API).

FILE: backend/modules/admet.py

Input schema:
  AdmetInput(ModuleInput):
    smiles_list: list[str]
    run_tier2: bool = True   # set False for quick filtering pass

TIER 1 — RDKit descriptors (run for ALL molecules, synchronous):

  For each SMILES, compute with RDKit:
  
  Lipinski Rule of Five:
    MW = Descriptors.MolWt(mol)         # < 500 → pass
    LogP = Descriptors.MolLogP(mol)     # < 5 → pass
    HBD = Descriptors.NumHDonors(mol)   # < 5 → pass
    HBA = Descriptors.NumHAcceptors(mol)# < 10 → pass
    lipinski_pass = all four rules pass
  
  Extended drug-likeness:
    TPSA = Descriptors.TPSA(mol)        # < 140 → pass (oral absorption)
    RotBonds = Descriptors.NumRotatableBonds(mol)  # < 10 → pass
    AromaticRings = Descriptors.NumAromaticRings(mol)
    QED = Chem.QED.qed(mol)             # 0-1, higher = more drug-like
    
  Structural alerts (PAINS filter):
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
    params = FilterCatalogParams()
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    catalog = FilterCatalog(params)
    has_pains = catalog.HasMatch(mol)   # True = likely assay interference
  
  Synthesizability:
    SA_score via rdkit.Contrib.SA_Score  # 1-10, lower = easier to synthesize
    sa_easy = sa_score < 4

TIER 2 — SwissADME (run async for top molecules only, max 20):

  POST to http://www.swissadme.ch/index.php
  Form data: smiles={smiles}
  Parse HTML response (use BeautifulSoup4) for:
    - GI absorption: "High" | "Low"
    - BBB permeant: "Yes" | "No"  
    - Pgp substrate: "Yes" | "No"
    - CYP1A2/2C9/2C19/2D6/3A4 inhibitor: "Yes" | "No" each
    - Bioavailability score: float 0-1
    - Log Kp (skin permeation): float
  
  Note: SwissADME may be slow or rate-limited.
  Use httpx with timeout=60s.
  If SwissADME fails for a molecule: return Tier 1 data only, add warning.

Traffic light scoring (apply to each molecule):
  GREEN: lipinski_pass AND NOT has_pains AND qed > 0.4 AND sa_easy
  AMBER: lipinski_pass AND (has_pains OR qed < 0.4 OR NOT sa_easy)
  RED: NOT lipinski_pass OR (tier2 available AND gi_absorption == "Low")

Overall assessment:
  "recommended" | "investigate" | "not_recommended"

Output per molecule:
  {
    "smiles": "...",
    "overall": "GREEN",
    "recommendation": "recommended",
    "tier1": {
      "mw": 412.5, "logp": 3.1, "hbd": 2, "hba": 5,
      "tpsa": 87.2, "rot_bonds": 6, "qed": 0.72,
      "lipinski_pass": true, "has_pains": false, "sa_score": 2.8,
      "lipinski_violations": []
    },
    "tier2": {
      "gi_absorption": "High", "bbb_permeant": "No",
      "pgp_substrate": "No", "cyp3a4_inhibitor": "No",
      "cyp2d6_inhibitor": "No", "cyp1a2_inhibitor": "Yes",
      "bioavailability_score": 0.55, "log_kp": -6.1
    },
    "flags": [
      {"type": "warning", "message": "CYP1A2 inhibitor — check drug interactions"},
      {"type": "info", "message": "Not CNS penetrant (BBB: No)"}
    ]
  }

This module runs synchronously for Tier 1 only (fast enough).
For Tier 2, create a separate Celery task.

FILE: backend/api/routes/admet.py

Route: POST /api/admet/predict
  - max 10000 SMILES per request
  - Tier 1 runs synchronously and returns immediately (< 5s for 1000 molecules)
  - If run_tier2=True AND list <= 100 molecules: runs Tier 2 async, returns job_id
  - If run_tier2=True AND list > 100: returns error asking user to reduce list first

Route: GET /api/admet/filter
  Query params: max_mw, max_logp, min_qed, require_lipinski, exclude_pains
  Takes a job_id, applies filters to its results, returns filtered SMILES list.
  Used by the pipeline to filter before docking.

FILE: backend/tests/test_admet.py

Tests:
1. test_aspirin: SMILES for aspirin → lipinski_pass=True, overall=GREEN
2. test_pains_detection: known PAINS compound → has_pains=True, overall=AMBER  
3. test_lipinski_fail: very large MW molecule → lipinski_pass=False, overall=RED
4. test_batch: 5 molecules → all 5 in output, each has tier1 data
5. test_traffic_light_logic: manually verify GREEN/AMBER/RED classification
```

---

### SPRINT 6 — Job Status & WebSocket Progress

> **Goal:** Frontend can poll job status AND receive real-time progress via WebSocket.  
> **Time:** 1 day  
> **Done when:** A running docking job streams "molecule 45/100 complete" live to the browser.

---

**Prompt:**

```
Context — read these files before starting:
- backend/core/queue.py
- backend/models/database.py
- backend/main.py

Implement the job status system with WebSocket progress streaming.

FILE: backend/core/websocket.py

Create a WebSocket connection manager:
  class ConnectionManager:
    - active_connections: dict[str, WebSocket]  # job_id -> socket
    - async connect(job_id, websocket)
    - disconnect(job_id)
    - async send_progress(job_id, message: dict)
    - async broadcast_to_job(job_id, data: dict)

Progress message format:
  {
    "job_id": "abc-123",
    "status": "running",
    "step": "docking",         # current pipeline step name
    "progress_pct": 45,        # 0-100
    "message": "Docking molecule 45 of 100",
    "completed_steps": ["target_lookup", "structure_fetch"],
    "current_step": "docking",
    "pending_steps": ["admet", "ranking"],
    "timestamp": "2024-01-15T10:23:45Z"
  }

Update queue.py so every Celery task calls:
  send_progress_update(job_id, step, pct, message)
  This function updates the Job record in DB AND publishes to Redis pubsub channel
  Channel name: f"job_progress:{job_id}"

FILE: backend/api/routes/jobs.py

Route: GET /api/jobs/{job_id}
  Returns full Job record including latest output_data and status.
  Used for polling (frontend polls every 3s as fallback).

Route: WebSocket /api/jobs/{job_id}/ws
  Connects client to real-time progress stream.
  Subscribes to Redis pubsub channel for this job.
  Streams all progress messages until job reaches "completed" or "failed".
  Sends current state immediately on connect (so late-joining clients catch up).
  Automatically closes when job completes.

Route: GET /api/jobs/
  Query params: user_id (optional), status, job_type, limit=20, offset=0
  Returns paginated list of jobs (for job history page).

Route: DELETE /api/jobs/{job_id}
  Cancels a running job (revokes Celery task) and marks as "cancelled".

Add to backend/models/schemas.py:
  JobProgressUpdate:
    job_id, status, step, progress_pct, message, 
    completed_steps, current_step, pending_steps, timestamp

Update all Celery tasks from previous sprints to emit progress:
  - lookup_target_task: emit at start (10%), after PDB fetch (50%), 
    after UniProt fetch (80%), on complete (100%)
  - predict_structure_task: emit at start (10%), after API response (80%), 
    after saving (100%)
  - dock_molecules_task: emit after each ligand (N/total * 100)
  - admet_task: emit after Tier 1 (40%), after each Tier 2 molecule, 
    on complete (100%)
```

---

### SPRINT 7 — Pipeline Orchestrator

> **Goal:** One endpoint that runs the full end-to-end pipeline and chains all modules.  
> **Time:** 2 days  
> **Done when:** POST /api/pipeline/run with an EGFR PDB ID and 10 SMILES returns a completed ranked list.

---

**Prompt:**

```
Context — read all files in backend/modules/ and backend/api/routes/ before starting.

Implement the pipeline orchestrator that chains all modules into one workflow.

FILE: backend/core/pipeline.py

The orchestrator accepts a PipelineConfig and runs the appropriate workflow:

  class PipelineConfig(BaseModel):
    job_id: str
    user_id: str | None
    
    # Target specification (one of):
    target_pdb_id: str | None = None
    target_uniprot_id: str | None = None
    target_sequence: str | None = None  # run ESMFold if provided
    target_lookup_job_id: str | None = None  # reuse previous lookup result
    
    # Task type:
    task: Literal["virtual_screening", "protein_design", "denovo_generation"]
    
    # Molecules (for virtual_screening):
    molecules: MoleculeInput | None = None
    # MoleculeInput: smiles_list | sdf_base64 | use_zinc_subset (bool)
    
    # Options:
    binding_site: dict | None = None
    admet_filter_before_docking: bool = True
    admet_min_qed: float = 0.4
    docking_exhaustiveness: int = 8
    max_molecules_to_dock: int = 500

VIRTUAL SCREENING WORKFLOW (task = "virtual_screening"):

  Step 1 — Resolve target:
    If target_pdb_id → fetch structure from PDB directly
    If target_uniprot_id → run TargetLookupModule → get best_pdb_id → fetch PDB
    If target_sequence → run StructurePredModule → get predicted PDB
    If target_lookup_job_id → load result from previous job in DB
    
    Emit progress: "step": "target_resolution", "progress_pct": 10

  Step 2 — Prepare molecules:
    If smiles_list → validate all with RDKit, remove invalid
    If sdf_base64 → decode, parse SDF with RDKit, extract SMILES
    If use_zinc_subset → load 5000 drug-like SMILES from local ZINC subset file
      (include a static file: backend/data/zinc_druglike_5000.smi)
    
    Emit progress: "step": "molecule_preparation", "progress_pct": 20

  Step 3 — Pre-docking ADMET filter (if admet_filter_before_docking=True):
    Run ADMET Tier 1 on ALL molecules (fast, synchronous)
    Keep only GREEN and AMBER molecules
    Keep top max_molecules_to_dock by QED score if list is too large
    
    Emit progress: "step": "admet_prefilter", "progress_pct": 30

  Step 4 — Molecular docking:
    Run DockingModule on filtered list
    Emit progress: "step": "docking", "progress_pct": 30→80 (proportional)

  Step 5 — Post-docking ADMET (Tier 2 on top 20 by docking score):
    Run ADMET Tier 2 on top 20 docked molecules
    Emit progress: "step": "admet_tier2", "progress_pct": 90

  Step 6 — Final ranking:
    Composite score = (normalised docking score * 0.6) + (QED * 0.25) + 
                      (lipinski_pass * 0.1) + (NOT has_pains * 0.05)
    Sort by composite score descending
    Add clinical context note for top 5 (call Claude API briefly):
      "Given this molecule binds {target} with affinity {score} kcal/mol,
       in 1 sentence: what is the most important next experimental step?"
    
    Emit progress: "step": "ranking", "progress_pct": 100

Final output:
  {
    "pipeline_summary": {
      "total_input_molecules": 500,
      "after_admet_prefilter": 312,
      "successfully_docked": 298,
      "top_candidates": 20
    },
    "target": { ...target info... },
    "ranked_candidates": [
      {
        "rank": 1,
        "smiles": "...",
        "composite_score": 0.84,
        "docking_affinity_kcal_mol": -9.2,
        "admet": { ...AdmetProfile... },
        "overall_flag": "GREEN",
        "next_step_suggestion": "Synthesise and test in EGFR T790M kinase activity assay",
        "pose_3d_path": "results/{job_id}/pose_1.pdbqt"
      }
    ],
    "structure_used": {"source": "PDB", "pdb_id": "7L9H", "resolution": 2.3},
    "binding_site": {"center_x": ..., ...}
  }

FILE: backend/api/routes/pipeline.py

Route: POST /api/pipeline/run
  - Accepts PipelineRequest (maps to PipelineConfig)
  - Validates: at least one target specification provided
  - Validates: if virtual_screening, molecules must be provided
  - Creates master Job record
  - Dispatches: run_pipeline_task (one Celery task that calls the orchestrator)
  - Returns: {job_id, estimated_minutes}

Add to queue.py:
  @celery_app.task(bind=True, max_retries=0, time_limit=7200)
  def run_pipeline_task(self, job_id: str, config_data: dict): ...
```

---

### SPRINT 8 — Frontend: Pipeline Wizard

> **Goal:** Build the full Step 1–6 wizard UI in Next.js.  
> **Time:** 5-7 days  
> **Done when:** User can complete the full flow from target entry to 3D result viewing.

---

**Prompt:**

```
Context — read frontend/lib/types.ts and frontend/lib/api.ts before starting.

Build the complete frontend pipeline wizard.
Design language: clean research tool — not a consumer app.
Use Tailwind utility classes only. Dark mode support throughout.
Font: use 'IBM Plex Mono' for protein sequences and SMILES, 
system-ui for everything else.

FILE: frontend/components/pipeline/PipelineWizard.tsx

Top-level state machine managing steps 1-6.
State:
  currentStep: 1-6
  selectedTarget: TargetLookupResponse | null
  selectedTask: "virtual_screening" | "protein_design" | "denovo_generation" | null
  molecules: MoleculeInput | null
  pipelineJobId: string | null
  results: PipelineResponse | null

Step gating: user cannot advance to Step N+1 until Step N is complete.
Show step indicator bar at top (dots or numbered pills).

FILE: frontend/components/target/TechnicalSearch.tsx

Input: accepts PDB IDs, UniProt accessions, protein names.
- Text input with placeholder: "EGFR, P00533, 1IEP, or search by name..."
- Autocomplete: debounced 300ms, calls GET /api/targets/search?q=
  Shows dropdown: protein name, organism, UniProt ID
- On submit: calls POST /api/targets/lookup → gets job_id → polls until complete
- Shows ProteinInfoCard on resolution

FILE: frontend/components/target/NaturalLanguageQuery.tsx

The AI-powered entry for non-technical users.
- Textarea: "Describe a disease, condition, or biological question..."
- 4 example query chips (clickable to populate textarea):
  "What proteins drive Alzheimer's progression?"
  "Why do lung cancers resist EGFR inhibitors?"
  "What causes Type 2 diabetes at the molecular level?"
  "Proteins involved in Parkinson's neurodegeneration"
- Submit button: "Find targets with AI"
- On submit: POST /api/ai/suggest-targets
- While loading: show animated thinking state with cycling messages:
  "Analysing disease mechanisms..."
  "Searching literature evidence..."  
  "Scoring druggability..."
  "Ranking by clinical relevance..."
- On response: render TargetSuggestionCard for each target

FILE: frontend/components/target/TargetSuggestionCard.tsx

Props: TargetSuggestion + onSelect callback
Display:
- Protein name (large) + confidence pill (HIGH/MEDIUM/LOW with colour)
- Gene symbol + UniProt ID in monospace
- mechanism_summary paragraph (12px, muted)
- druggability_note in a subtle callout box
- Tags row: colour-coded pills for pathway, structure status, clinical stage
- "Select this target →" button
Selected state: card gets purple border + checkmark

FILE: frontend/components/target/ProteinInfoCard.tsx

Shows after a target is resolved (either mode).
Display:
- Protein name + organism + gene symbol
- Stats row: sequence length, PDB count, best resolution
- Structure badge: "PDB 7L9H · 2.3Å · X-ray · has ligand (Osimertinib)"
  or "AlphaFold prediction available" if no experimental structure
- Disease associations as tags
- "Use this target" confirmation button

FILE: frontend/components/pipeline/Step1Target.tsx

Combines the two modes with a toggle:
  [Technical search] [Ask in plain language]
Renders TechnicalSearch or NaturalLanguageQuery based on active mode.
Both modes confirm into the same ProteinInfoCard at the bottom.

FILE: frontend/components/pipeline/Step2Task.tsx

Three task cards:
  Virtual screening — "Test molecules against this target"
    Show: accepts SMILES list, SDF file, or ZINC subset
  Protein design — "Design a novel protein binder with AI"  
    Show: RFdiffusion + ProteinMPNN pipeline, GPU required
  De novo generation — "Generate new molecules from scratch"
    Show: REINVENT generative model

FILE: frontend/components/pipeline/Step3Structure.tsx

Shows the resolved structure info.
If PDB found: show green banner "Experimental structure found — PDB {id}"
If predicted: show amber banner "No experimental structure — predicting with ESMFold"
Show a placeholder 3D viewer box (the real viewer is in Step 6 after results).
Show binding site info if auto-detected.
"Confirm and run pipeline" button.

FILE: frontend/components/pipeline/Step4Running.tsx

Live progress view while job runs.
Props: jobId
- Connects to WebSocket /api/jobs/{jobId}/ws
- Falls back to polling GET /api/jobs/{jobId} every 3s if WS fails
- Shows:
  Progress bar (animated, width = progress_pct%)
  Current step name with spinner
  Step checklist: each step shows pending/running/complete icon
  Last message text ("Docking molecule 47 of 312...")
  Elapsed time counter
- On completion: automatically advances to Step 5

FILE: frontend/components/pipeline/Step5Results.tsx

Props: PipelineResponse
- Summary stats bar: X input → Y after filter → Z docked → top 20
- Sortable table: rank, 2D structure thumbnail (call RDKit endpoint), 
  docking affinity, ADMET overall (GREEN/AMBER/RED dot), 
  composite score, action buttons
- Each row expandable: full ADMET breakdown with flags
  (render AdmetBadge per property)
- Top 3 rows show next_step_suggestion from AI
- Download buttons: CSV, SDF, JSON
- "View in 3D" button per row → advances to Step 6

FILE: frontend/components/pipeline/Step6Viewer.tsx

3D structure viewer using 3Dmol.js.
Load from CDN: https://3Dmol.csb.pitt.edu/build/3Dmol-min.js
(do NOT import as npm package — use CDN via useEffect script injection)

On mount:
  1. Load receptor PDB: GET /api/structures/{job_id}/download
  2. Load best ligand pose PDBQT from results
  3. Render: protein as cartoon (grey), binding pocket as surface (purple, 50% opacity),
     ligand as sticks (amber/orange coloured)
  4. Camera: focus on ligand centroid

Controls panel:
  - Toggle: cartoon / surface / stick for protein
  - Colour scheme: by chain / by element / by residue type
  - Show/hide: water molecules, hydrogens
  - Measure distance button (click two atoms)
  - "Compare with known drug" — loads Osimertinib if EGFR target
  - Download image button (3Dmol snapshot)

Back/forward buttons to cycle through top 5 poses.

FILE: frontend/lib/websocket.ts

Custom hook: useJobWebSocket(jobId: string)
Returns: { progress: JobProgressUpdate | null, isConnected: boolean }
Handles: connection, reconnection (3 attempts), fallback to polling.
```

---

### SPRINT 9 — Molecule 2D Rendering Endpoint + SDF Export

> **Goal:** Backend renders 2D molecule images from SMILES; users can download SDF files.  
> **Time:** 1 day  
> **Done when:** Results table shows 2D structure thumbnails for each candidate.

---

**Prompt:**

```
Context: read backend/modules/admet.py for RDKit usage patterns.

Add two utility endpoints to the backend.

FILE: backend/api/routes/molecules.py

Route: GET /api/molecules/render?smiles={smiles}&size=200
  Uses RDKit to render a 2D structure image:
    from rdkit import Chem
    from rdkit.Chem import Draw
    mol = Chem.MolFromSmiles(smiles)
    img = Draw.MolToImage(mol, size=(size, size))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
  Returns: PNG image with Content-Type: image/png
  Cache header: Cache-Control: public, max-age=86400 (SMILES → image is deterministic)
  Error: if invalid SMILES, return a placeholder "invalid structure" image

Route: POST /api/molecules/export-sdf
  Body: { job_id: str, indices: list[int] | None }  (None = export all)
  Reads ranked_candidates from job result in DB
  For each molecule: generate 3D conformer with RDKit, write to SDF
  Returns: SDF file download with Content-Disposition header

Route: POST /api/molecules/validate
  Body: { smiles_list: list[str] }
  Fast validation — returns for each: {smiles, valid: bool, error: str | None}
  Used by frontend to validate user-pasted SMILES before submitting pipeline

In frontend/components/molecule/SmilesInput.tsx:
  Add:
  - Paste textarea + file upload for SDF
  - On paste: call POST /api/molecules/validate, 
    show per-line green check or red X
  - Show count: "312 valid molecules · 8 invalid (highlighted)"
  - "Use ZINC drug-like subset (5000 molecules)" checkbox option
  
In frontend/components/molecule/MoleculeCard.tsx:
  Display:
  - 2D image: <img src={/api/molecules/render?smiles={encodeURIComponent(smiles)}} />
  - SMILES string in monospace, truncated with copy button
  - Docking score badge
  - ADMET overall dot (green/amber/red)
```

---

### SPRINT 10 — Polish, Error States, Job History

> **Goal:** Production-ready error handling, empty states, and job history page.  
> **Time:** 2 days  
> **Done when:** All error states are handled gracefully and users can browse past jobs.

---

**Prompt:**

```
Context: read all frontend/components/ files before starting.

Add production-quality error handling and the job history page.

ERROR STATES — add to every step component:

Step 1 (Target):
  - Target not found in PDB or UniProt: "No structure found — we'll predict it 
    with ESMFold. This takes 2-5 minutes."
  - AI query API error: "AI target suggestion unavailable. 
    Switch to technical search to continue."

Step 3 (Structure):
  - ESMFold fails: "Structure prediction failed. You can upload a PDB file manually."
  - Add: file upload input for manual PDB upload (POST /api/structures/upload)

Step 4 (Running):
  - Job fails mid-pipeline: show which step failed, error message, 
    and "retry from this step" button
  - Job timeout (>60 min): show timeout message with contact info

Step 5 (Results):
  - No molecules passed docking threshold: 
    "No molecules achieved binding affinity < -5.0 kcal/mol. 
     Try: broader ADMET filters, more molecules, or a different target region."
  - All molecules failed ADMET: similar message with suggestions

EMPTY STATES:
  - First visit (no jobs): welcoming empty state on the wizard start
    "Start by entering a protein target or describing your disease of interest"
  - No job history: "Your previous experiments will appear here"

FILE: frontend/app/library/page.tsx — Job History

Display all past pipeline jobs for this user:
  Calls GET /api/jobs/?limit=20&offset={page*20}
  Table/card view showing:
    - Target name + job type + date
    - Status badge (completed / failed / running)
    - Top result preview (molecule rank 1 score if completed)
    - "View results" / "Resume" / "Delete" actions

Add pagination (20 per page).

LOADING SKELETONS:
  Add Tailwind skeleton loaders (animate-pulse) for:
  - ProteinInfoCard while loading
  - TargetSuggestionCard list while AI query runs
  - Results table while pipeline runs

GLOBAL ERROR BOUNDARY:
  frontend/app/error.tsx — catches unhandled React errors
  Shows: "Something went wrong" + reload button + error ID for debugging

BACKEND ERROR LOGGING:
  Add structured logging throughout the backend:
  Every error logged with: job_id, module_name, error_type, timestamp
  Use Python's logging module — NOT print() anywhere in the codebase
  Log format: JSON (for future log aggregation)
```

---

## 7. Docker Compose Reference

```yaml
# This is the target state — Sprint 0 creates this file

version: "3.9"

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes: ["./backend:/app", "./data:/data"]
    depends_on: [postgres, redis, minio]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env
    volumes: ["./frontend:/app"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: drugdiscovery
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes: ["pgdata:/var/lib/postgresql/data"]
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

  celery_worker:
    build: ./backend
    command: celery -A core.queue worker --loglevel=info --concurrency=4
    env_file: .env
    volumes: ["./backend:/app", "./data:/data"]
    depends_on: [redis, postgres, minio]

  celery_flower:
    build: ./backend
    command: celery -A core.queue flower --port=5555
    ports: ["5555:5555"]
    depends_on: [redis]

volumes:
  pgdata:
  miniodata:

networks:
  default:
    name: drug-discovery-net
```

---

## 8. Key Environment Variables

```bash
# .env (copy from .env.example)

# Anthropic (required for AI query module)
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql+asyncpg://admin:secret@postgres:5432/drugdiscovery
REDIS_URL=redis://redis:6379/0

# Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_SSL=false

# External APIs (these are free/public)
ESMFOLD_API_URL=https://api.esmatlas.com/foldSequence/v1/pdb/
ALPHAFOLD_DB_URL=https://alphafold.ebi.ac.uk/files
PDB_API_URL=https://data.rcsb.org/rest/v1/core
UNIPROT_API_URL=https://rest.uniprot.org/uniprotkb

# App
APP_ENV=development
LOG_LEVEL=INFO
MAX_MOLECULES_PER_JOB=10000
```

---

## 9. Sprint Order & Checklist

Run these in exact order. Check off each before proceeding.

```
[ ] Sprint 0  — Scaffold          docker compose up → all services healthy
[ ] Sprint 1  — AI Query          POST /api/ai/suggest-targets returns targets
[ ] Sprint 2  — Target Lookup     EGFR lookup returns full protein card
[ ] Sprint 3  — Structure Pred    ESMFold wrapper returns PDB + pLDDT
[ ] Sprint 4  — Docking           10 SMILES docked, sorted by affinity
[ ] Sprint 5  — ADMET             10 molecules get traffic-light scores
[ ] Sprint 6  — Job/WebSocket     Live progress streams during docking
[ ] Sprint 7  — Pipeline          Full end-to-end run completes
[ ] Sprint 8  — Frontend Wizard   Step 1-6 UI wired to real API
[ ] Sprint 9  — 2D Render/Export  Molecule thumbnails + SDF download
[ ] Sprint 10 — Polish            Error states, history, loading skeletons
```

---

## 10. How to Start Each Claude Code Session

At the beginning of every Claude Code session after Sprint 0:

```
Read CLAUDE.md first.

Then read: [list the specific files relevant to this sprint]

Now implement Sprint N: [paste the sprint prompt]
```

Never skip the "read CLAUDE.md first" instruction.
It keeps Claude Code consistent across sessions.
```
