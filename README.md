# Drug Discovery Platform

End-to-end drug discovery simulation platform for both technical researchers and non-technical users.

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |
| MinIO Console | http://localhost:9001 |

## Six-Step Pipeline

1. **Find target** — PDB/UniProt search or natural-language AI query
2. **Choose task** — virtual screening / protein design / de novo generation
3. **Structure** — auto-fetch from PDB or predict with ESMFold
4. **Run pipeline** — docking + ADMET execute async in background
5. **Results** — ranked candidates with binding scores + ADMET flags
6. **3D inspection** — protein + ligand visualised in 3Dmol.js
