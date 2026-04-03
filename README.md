# Drug Discovery Platform

End-to-end drug discovery simulation platform. Describe a disease, find protein targets, screen molecules, and get ranked drug candidates — all in one workflow.

**[Full Documentation](docs/DOCUMENTATION.md)**

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
docker compose up --build -d
```

Open http://localhost:3000 and start your first pipeline.

## What it does

| Step | What happens |
|------|-------------|
| 1. Find target | Describe a disease ("Alzheimer's") or search by protein name/PDB ID |
| 2. Choose task | Virtual Screening, Protein Design, or De Novo Generation |
| 3. Structure | Auto-fetch 3D structure from PDB or predict with ESMFold |
| 4. Run pipeline | Docking + ADMET execute async in background |
| 5. Results | Ranked candidates with binding scores + ADMET traffic lights |
| 6. 3D viewer | Interactive protein visualization with 3Dmol.js |

## Three Pipeline Modes

- **Virtual Screening** — Dock molecules against a protein target using AutoDock Vina. Real docking with fpocket pocket detection, ADMET filtering, and composite scoring.
- **Protein Design** — AI designs novel protein binder sequences targeting the binding site. Returns sequences with predicted pLDDT scores and binding strategies.
- **De Novo Generation** — AI generates novel drug-like molecules from scratch. Validated by RDKit, scored with Lipinski/PAINS/QED ADMET.

## Tech Stack

**Backend**: FastAPI + Celery + Redis + PostgreSQL + MinIO + RDKit + AutoDock Vina

**Frontend**: Next.js 14 + TypeScript + Tailwind CSS + 3Dmol.js

**AI**: Claude Sonnet 4.6 (target discovery, protein design, molecule generation)

## Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |
| MinIO Console | http://localhost:9001 |

## Tests

```bash
cd backend && uv sync --extra dev && uv run pytest tests/ -v
# 52 tests covering all modules
```

## License

See individual component licenses (RDKit: BSD, Vina: Apache 2.0, fpocket: MIT).
