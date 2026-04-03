# Drug Discovery Platform - Complete Documentation

## What is this platform?

This is an end-to-end drug discovery simulation platform that helps you find potential drug molecules for any disease. You describe a disease (like "Alzheimer's" or "lung cancer"), and the platform:

1. **Finds protein targets** that cause the disease
2. **Fetches the 3D structure** of those proteins from scientific databases
3. **Tests thousands of molecules** against the protein to find ones that bind well
4. **Scores each molecule** for drug-likeness, toxicity, and synthesizability
5. **Ranks the best candidates** and shows you the results with a 3D viewer

The platform supports three modes:

| Mode | What it does | Who it's for |
|------|-------------|--------------|
| **Virtual Screening** | Tests existing molecules against a protein target using AutoDock Vina docking | Researchers with a compound library |
| **Protein Design** | Designs novel protein binders that could interact with the target | Protein engineers |
| **De Novo Generation** | Generates entirely new drug-like molecules from scratch using AI | Medicinal chemists exploring new scaffolds |

---

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- An Anthropic API key (for AI-powered features)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/jubaer145/drug_discovery_platform.git
cd drug_discovery_platform

# 2. Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start all services
docker compose up --build -d

# 4. Wait ~2 minutes for all services to start, then open:
#    Frontend:  http://localhost:3000
#    API Docs:  http://localhost:8000/docs
#    Flower:    http://localhost:5555
```

### Verify everything is running

```bash
# Check all containers are up
docker compose ps

# Check backend health
curl http://localhost:8000/health
# Should return: {"status":"ok","version":"0.1.0"}
```

---

## User Guide

### Step 1: Find Your Target

When you open `http://localhost:3000`, you see the Pipeline Wizard starting at Step 1.

**Option A: Describe Disease (AI-powered)**
- Click "Describe Disease" tab
- Type a disease description, e.g., "What proteins drive Alzheimer's disease?"
- Click "Find Drug Targets"
- The AI (Claude) analyzes your question and returns 3-5 protein targets with:
  - Protein name and gene symbol
  - Confidence level (high/medium/low)
  - Clinical stage (approved, phase 3, preclinical)
  - Difficulty rating
  - Mechanism explanation
- Click on a target card to select it

**Option B: Technical Search**
- Click "Technical Search" tab
- Type a protein name (EGFR), UniProt ID (P00533), or PDB ID (1IEP)
- Autocomplete dropdown shows matching proteins from UniProt
- Click to select

### Step 2: Choose Your Task

After selecting a target, choose what you want to do:

**Virtual Screening**
- Tests a library of molecules against your target
- Paste SMILES strings (one per line) or check "Use ZINC drug-like subset (5,000 molecules)"
- Example SMILES: `CC(=O)Oc1ccccc1C(=O)O` (aspirin)

**Protein Design**
- AI designs novel protein binder sequences for the target
- Choose number of designs (4-20)
- Returns amino acid sequences with predicted confidence scores

**De Novo Generation**
- AI generates completely new drug-like molecules targeting your protein
- Choose number of molecules (10-100)
- Generated molecules are validated by RDKit and scored with ADMET

### Step 3: Confirm Structure

Review the target information:
- Green banner = experimental PDB structure found
- Amber banner = will predict structure with ESMFold
- Click "Confirm and Run Pipeline"

### Step 4: Running

The pipeline executes in the background. You see:
- Progress bar with percentage
- Step checklist (target resolution, ADMET filter, docking, etc.)
- Elapsed time counter
- The page auto-advances to Results when complete

### Step 5: Results

**Virtual Screening results:**
- Summary: input molecules -> after ADMET filter -> successfully docked -> top candidates
- Ranked table: rank, SMILES, binding affinity (kcal/mol), composite score, ADMET flag (green/amber/red)
- Click a row to expand ADMET details (MW, LogP, HBD, HBA, TPSA, QED, etc.)

**Protein Design results:**
- Summary: number of designs, average pLDDT score
- Design strategy explanation
- Each design shows: name, pLDDT score, amino acid sequence, binding strategy, key residues, estimated affinity

**De Novo Generation results:**
- Summary: generated count, GREEN/AMBER/RED counts
- Table: SMILES, composite score, ADMET flag

### Step 6: 3D Viewer

- Shows the protein structure rendered in 3Dmol.js
- Spectrum coloring (blue N-terminus to red C-terminus)
- Interactive: rotate (drag), zoom (scroll), pan (right-drag)

### Job History

Click "History" in the nav bar to see all past pipeline runs with status badges, timestamps, and links to detailed results.

---

## Architecture Overview

### System Diagram

```
                    User Browser (localhost:3000)
                           |
                    +--------------+
                    |   Next.js    |
                    |   Frontend   |
                    +------+-------+
                           | REST + WebSocket
                    +------v-------+
                    |   FastAPI    |
                    |   Backend    |  localhost:8000
                    +--+---+---+--+
                       |   |   |
          +------------+   |   +-------------+
          |                |                 |
    +-----v-----+  +------v------+  +-------v-------+
    |  Celery   |  | PostgreSQL  |  |    MinIO       |
    |  Worker   |  | (jobs, data)|  | (PDB, SDF,     |
    |           |  +-------------+  |  results)      |
    +-----+-----+                   +----------------+
          |
    +-----v-----+
    |   Redis   |
    | (queue +  |
    |  pubsub)  |
    +-----------+

External APIs:
  - Anthropic Claude (AI target discovery)
  - RCSB PDB (protein structures)
  - UniProt (protein data)
  - ESMFold (structure prediction)
  - AlphaFold DB (predicted structures)
```

### Backend Modules

Each module inherits from `BaseModule` and implements `validate_input()` and `run()`:

| Module | File | Purpose | External Dependency |
|--------|------|---------|-------------------|
| AI Query | `modules/ai_query.py` | Translate disease to protein targets | Claude API |
| Target Lookup | `modules/target_lookup.py` | Fetch protein data from PDB/UniProt | PDB + UniProt APIs |
| Structure Prediction | `modules/structure_pred.py` | Predict 3D structure from sequence | ESMFold API |
| Docking | `modules/docking.py` | Dock molecules against protein | AutoDock Vina + OpenBabel + fpocket |
| ADMET | `modules/admet.py` | Score drug-likeness and toxicity | RDKit (local) |
| Protein Design | `modules/protein_design.py` | Design protein binder sequences | Claude API |
| Molecule Generation | `modules/mol_generation.py` | Generate novel drug molecules | Claude API + RDKit validation |

### Pipeline Orchestrator

`backend/core/pipeline.py` chains modules into end-to-end workflows:

**Virtual Screening**: Target resolution -> molecule preparation -> ADMET pre-filter -> docking (Vina) -> post-docking ADMET -> composite ranking

**Protein Design**: Target resolution -> fetch PDB -> Claude AI designs binder sequences -> scoring

**De Novo Generation**: Target resolution -> Claude AI generates SMILES -> RDKit validation -> ADMET scoring

### Composite Score Formula (Virtual Screening)

```
Score = (normalized_affinity x 0.60) + (QED x 0.25) + (lipinski_pass x 0.10) + (no_PAINS x 0.05)
```

### ADMET Traffic Light System

| Color | Meaning | Criteria |
|-------|---------|----------|
| GREEN | Recommended | Lipinski pass + no PAINS + QED > 0.4 + SA score < 4 |
| AMBER | Investigate | Lipinski pass but has warnings |
| RED | Not recommended | Lipinski fail or poor absorption |

---

## API Reference

### Health Check

```
GET /health
Response: {"status": "ok", "version": "0.1.0"}
```

### AI Target Discovery

```
POST /api/ai/suggest-targets
Body: {"query": "What proteins drive Alzheimer's disease?", "max_targets": 5}
Response: {
  "targets": [
    {
      "protein_name": "BACE1",
      "gene_symbol": "BACE1",
      "uniprot_id": "P56817",
      "confidence": "high",
      "clinical_stage": "phase3_trials",
      "difficulty": "moderate",
      "mechanism_summary": "...",
      "druggability_note": "...",
      "tags": ["amyloid pathway"],
      "has_pdb_structure": true
    }
  ],
  "query_interpretation": "...",
  "confidence_explanation": "..."
}
```

### Target Lookup

```
POST /api/targets/lookup
Body: {"query": "EGFR"}
Response: {"job_id": "uuid", "status": "pending"}

GET /api/targets/search?q=EGFR&limit=5
Response: [{"uniprot_id": "P00533", "protein_name": "Epidermal growth factor receptor", "gene_symbol": "EGFR", "organism": "Homo sapiens"}]
```

### ADMET Prediction

```
POST /api/admet/predict
Body: {"smiles_list": ["CC(=O)Oc1ccccc1C(=O)O", "CCO"]}
Response: {
  "job_id": "uuid",
  "status": "completed",
  "total": 2,
  "profiles": [
    {
      "smiles": "CC(=O)Oc1ccccc1C(=O)O",
      "overall": "GREEN",
      "recommendation": "recommended",
      "tier1": {"mw": 180.16, "logp": 1.31, "hbd": 1, "hba": 3, "tpsa": 63.6, "qed": 0.55, "lipinski_pass": true, "has_pains": false, "sa_score": 1.58}
    }
  ]
}
```

### Run Full Pipeline

```
POST /api/pipeline/run
Body: {
  "target_uniprot_id": "P56817",
  "task_type": "virtual_screening",
  "molecules": {"smiles": ["CC(=O)Oc1ccccc1C(=O)O", "CCO"]},
  "admet_filter_before_docking": true
}
Response: {"job_id": "uuid", "status": "pending", "estimated_minutes": 2}
```

### Job Status

```
GET /api/jobs/{job_id}
Response: {
  "id": "uuid",
  "status": "completed",
  "job_type": "pipeline",
  "output_data": { ... pipeline results ... },
  "created_at": "2026-04-01T12:00:00Z"
}
```

### Molecule 2D Rendering

```
GET /api/molecules/render?smiles=CC(=O)Oc1ccccc1C(=O)O&size=200
Response: PNG image (image/png)
```

### SDF Export

```
POST /api/molecules/export-sdf
Body: {"job_id": "uuid", "smiles_list": ["CCO", "c1ccccc1"]}
Response: SDF file download
```

### File Download

```
GET /api/files/{bucket}/{path}
Example: GET /api/files/structures/job-id/receptor.pdb
Response: File content (PDB, JSON, SDF, etc.)
```

---

## Configuration

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | API key for Claude AI features |
| `DATABASE_URL` | No | `postgresql+asyncpg://admin:secret@postgres:5432/drugdiscovery` | PostgreSQL connection |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis for Celery + cache |
| `MINIO_ENDPOINT` | No | `minio:9000` | MinIO S3 endpoint |
| `MINIO_ACCESS_KEY` | No | `minioadmin` | MinIO credentials |
| `MINIO_SECRET_KEY` | No | `minioadmin` | MinIO credentials |
| `ESMFOLD_API_URL` | No | `https://api.esmatlas.com/foldSequence/v1/pdb/` | ESMFold prediction API |
| `PDB_API_URL` | No | `https://data.rcsb.org/rest/v1` | RCSB PDB REST API |
| `UNIPROT_API_URL` | No | `https://rest.uniprot.org/uniprotkb` | UniProt REST API |

---

## Development Guide

### Running Tests

```bash
cd backend

# Install dev dependencies
uv sync --extra dev

# Run all tests (52 tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_admet.py -v

# Run with coverage
uv run pytest tests/ --cov=modules --cov=core
```

### Test Files

| File | Tests | What it covers |
|------|-------|---------------|
| `test_ai_query.py` | 4 | AI target discovery with mocked Claude |
| `test_target_lookup.py` | 6 | PDB/UniProt/name lookups with mocked httpx |
| `test_structure_pred.py` | 6 | ESMFold API + pLDDT parsing |
| `test_docking.py` | 6 | Vina parsing, pocket detection, partial failures |
| `test_admet.py` | 6 | Aspirin, PAINS, Lipinski, traffic lights |
| `test_jobs.py` | 8 | WebSocket manager, Redis progress, job API |
| `test_pipeline.py` | 11 | Molecule prep, ranking, full pipeline with mocks |
| `test_molecules.py` | 5 | 2D rendering, SDF export, validation |

### Adding a New Module

1. Create `backend/modules/your_module.py`:
```python
from .base import BaseModule, ModuleInput, ModuleOutput
from models.schemas import YourInput

class YourModule(BaseModule):
    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, YourInput):
            return False, "Input must be YourInput"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        # Your logic here
        return ModuleOutput(job_id=input.job_id, status="completed", data={...})
```

2. Add input schema to `backend/models/schemas.py`
3. Add route in `backend/api/routes/`
4. Add Celery task in `backend/core/queue.py`
5. Write tests in `backend/tests/`

### Docker Tools Installed

The backend Docker image includes:
- **AutoDock Vina v1.2.5** — molecular docking (`/usr/local/bin/vina`)
- **OpenBabel 3.1** — format conversion (`/usr/local/bin/obabel`)
- **fpocket** — binding pocket detection (`/usr/local/bin/fpocket`)
- **RDKit** — cheminformatics (Python package)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5432 already in use | You have PostgreSQL running on host. Docker uses internal networking, so this is OK. |
| Backend won't start | Check `docker logs drug_discovery_platform-backend-1` for errors |
| AI features don't work | Verify `ANTHROPIC_API_KEY` is set in `.env` |
| Docking returns no results | Check that Vina/obabel are installed: `docker exec celery_worker vina --version` |
| Frontend shows "coming soon" | Restart frontend: `docker restart drug_discovery_platform-frontend-1` |
| WebSocket not connecting | Normal — falls back to 3-second polling automatically |
