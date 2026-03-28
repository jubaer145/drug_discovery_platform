import base64
import logging
import uuid

import httpx
from rdkit import Chem

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.storage import upload_file, download_file
from core.websocket import send_progress_update
from models.schemas import (
    PipelineConfig, PipelineRequest, PipelineResponse,
    TargetLookupInput, StructurePredInput, DockingInput, AdmetInput,
    MoleculeInput,
)
from modules.target_lookup import TargetLookupModule
from modules.structure_pred import StructurePredModule
from modules.docking import DockingModule
from modules.admet import AdmetModule

logger = logging.getLogger(__name__)

ALL_STEPS = [
    "target_resolution",
    "molecule_preparation",
    "admet_prefilter",
    "docking",
    "admet_tier2",
    "ranking",
]


def _progress(job_id: str, step: str, pct: int, msg: str, **kwargs):
    idx = ALL_STEPS.index(step) if step in ALL_STEPS else 0
    send_progress_update(
        job_id, step, pct, msg,
        completed_steps=ALL_STEPS[:idx],
        pending_steps=ALL_STEPS[idx + 1:],
        **kwargs,
    )


async def dispatch_pipeline(request: PipelineRequest, db: AsyncSession) -> PipelineResponse:
    """Dispatch pipeline as a Celery task. Returns immediately."""
    from core.queue import run_pipeline_task
    from models.database import Job

    job_id = str(uuid.uuid4())

    config_data = {
        "target_pdb_id": request.target_pdb_id or request.target_pdb_path,
        "target_uniprot_id": request.target_uniprot_id,
        "target_sequence": request.target_sequence,
        "task": request.task_type,
        "molecules": request.molecules.model_dump() if request.molecules else None,
        "binding_site": request.binding_site,
        "admet_filter_before_docking": request.admet_filter_before_docking,
        "docking_exhaustiveness": request.docking_exhaustiveness,
        "max_molecules_to_dock": request.max_molecules_to_dock,
    }

    # Create Job record in DB so polling works
    job = Job(
        id=uuid.UUID(job_id),
        job_type="pipeline",
        status="pending",
        input_data=config_data,
    )
    db.add(job)
    await db.commit()

    # Estimate time: ~1 min base + 0.5 min per 100 molecules
    mol_count = 0
    if request.molecules and request.molecules.smiles:
        mol_count = len(request.molecules.smiles)
    elif request.molecules and request.molecules.use_zinc_subset:
        mol_count = 5000
    estimated = max(2, 1 + mol_count // 200)

    run_pipeline_task.delay(job_id, config_data)
    return PipelineResponse(job_id=job_id, status="pending", estimated_minutes=estimated)


def run_virtual_screening(job_id: str, config: PipelineConfig) -> dict:
    """Execute the full virtual screening pipeline synchronously (runs inside Celery)."""

    # Step 1 — Resolve target
    _progress(job_id, "target_resolution", 5, "Resolving target...")
    target_info, pdb_path = _resolve_target(job_id, config)
    if pdb_path is None:
        return _fail(job_id, "Could not resolve target structure")
    _progress(job_id, "target_resolution", 10, "Target resolved")

    # Step 2 — Prepare molecules
    _progress(job_id, "molecule_preparation", 15, "Preparing molecules...")
    smiles_list = _prepare_molecules(config.molecules)
    if not smiles_list:
        return _fail(job_id, "No valid molecules to screen")
    total_input = len(smiles_list)
    _progress(job_id, "molecule_preparation", 20, f"Prepared {total_input} molecules")

    # Step 3 — Pre-docking ADMET filter
    after_filter = total_input
    if config.admet_filter_before_docking:
        _progress(job_id, "admet_prefilter", 25, "Running ADMET pre-filter...")
        smiles_list = _admet_prefilter(
            job_id, smiles_list, config.admet_min_qed, config.max_molecules_to_dock,
        )
        after_filter = len(smiles_list)
        _progress(job_id, "admet_prefilter", 30, f"ADMET filter: {after_filter}/{total_input} pass")

    if not smiles_list:
        return _fail(job_id, "All molecules filtered out by ADMET pre-screen")

    # Step 4 — Docking
    _progress(job_id, "docking", 35, f"Docking {len(smiles_list)} molecules...")
    docking_results = _run_docking(job_id, pdb_path, smiles_list, config)
    docked_count = len(docking_results)
    _progress(job_id, "docking", 80, f"Docked {docked_count} molecules")

    if not docking_results:
        return _fail(job_id, "Docking produced no results")

    # Step 5 — Post-docking ADMET on top 20
    top_smiles = [r["smiles"] for r in docking_results[:20]]
    _progress(job_id, "admet_tier2", 85, f"Running ADMET on top {len(top_smiles)} candidates...")
    admet_profiles = _run_admet_tier2(job_id, top_smiles)
    _progress(job_id, "admet_tier2", 90, "ADMET Tier 2 complete")

    # Step 6 — Final ranking
    _progress(job_id, "ranking", 92, "Computing composite scores...")
    ranked = _rank_candidates(docking_results[:20], admet_profiles)
    _progress(job_id, "ranking", 100, "Pipeline complete", status="completed")

    return {
        "pipeline_summary": {
            "total_input_molecules": total_input,
            "after_admet_prefilter": after_filter,
            "successfully_docked": docked_count,
            "top_candidates": len(ranked),
        },
        "target": target_info,
        "ranked_candidates": ranked,
        "structure_used": {
            "source": target_info.get("source", "unknown"),
            "pdb_id": target_info.get("best_pdb_id"),
        },
        "binding_site": config.binding_site,
    }


# ------------------------------------------------------------------
# Step implementations
# ------------------------------------------------------------------

def _resolve_target(job_id: str, config: PipelineConfig) -> tuple[dict, str | None]:
    """Resolve target to a PDB file path in MinIO."""

    if config.target_pdb_id:
        # Fetch PDB from RCSB
        pdb_id = config.target_pdb_id.upper()
        if "/" in pdb_id:
            # Already a MinIO path
            return {"source": "minio", "pdb_path": pdb_id}, pdb_id

        try:
            with httpx.Client(timeout=30.0) as client:
                url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
                resp = client.get(url)
                resp.raise_for_status()
                pdb_data = resp.content
        except Exception as e:
            logger.error(f"Failed to fetch PDB {pdb_id}: {e}")
            return {"error": str(e)}, None

        key = f"{job_id}/receptor.pdb"
        upload_file("structures", key, pdb_data, "chemical/x-pdb")
        return {
            "source": "PDB",
            "best_pdb_id": pdb_id,
        }, f"structures/{key}"

    if config.target_uniprot_id:
        module = TargetLookupModule()
        result = module.execute(TargetLookupInput(
            job_id=f"{job_id}_lookup", query=config.target_uniprot_id,
        ))
        if result.status != "completed" or not result.data:
            return {"error": "Target lookup failed"}, None

        best_pdb = result.data.get("best_pdb_id")
        if best_pdb:
            # Fetch the PDB
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(f"https://files.rcsb.org/download/{best_pdb}.pdb")
                    resp.raise_for_status()
                    key = f"{job_id}/receptor.pdb"
                    upload_file("structures", key, resp.content, "chemical/x-pdb")
                    result.data["source"] = "PDB_via_UniProt"
                    return result.data, f"structures/{key}"
            except Exception:
                pass

        return result.data, None

    if config.target_sequence:
        module = StructurePredModule()
        result = module.execute(StructurePredInput(
            job_id=f"{job_id}_structure", sequence=config.target_sequence,
        ))
        if result.status != "completed":
            return {"error": "Structure prediction failed"}, None

        return {
            "source": "ESMFold",
            "mean_plddt": result.data.get("mean_plddt"),
            "quality": result.data.get("quality_assessment"),
        }, result.data.get("pdb_url")

    return {"error": "No target specification provided"}, None


def _prepare_molecules(molecules: MoleculeInput | None) -> list[str]:
    """Parse and validate input molecules."""
    if molecules is None:
        return []

    smiles_list = []

    if molecules.smiles:
        for smi in molecules.smiles:
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                smiles_list.append(Chem.MolToSmiles(mol))  # canonicalize

    if molecules.sdf_base64:
        try:
            sdf_bytes = base64.b64decode(molecules.sdf_base64)
            suppl = Chem.SDMolSupplier()
            suppl.SetData(sdf_bytes.decode("utf-8"))
            for mol in suppl:
                if mol is not None:
                    smiles_list.append(Chem.MolToSmiles(mol))
        except Exception as e:
            logger.warning(f"SDF parsing error: {e}")

    if molecules.use_zinc_subset:
        smiles_list.extend(_load_zinc_subset())

    # Deduplicate
    return list(dict.fromkeys(smiles_list))


def _load_zinc_subset() -> list[str]:
    """Load ZINC drug-like subset from static file."""
    import os
    zinc_path = os.path.join(os.path.dirname(__file__), "..", "data", "zinc_druglike_5000.smi")
    if not os.path.exists(zinc_path):
        logger.warning("ZINC subset file not found, returning empty list")
        return []
    with open(zinc_path) as f:
        return [line.strip().split()[0] for line in f if line.strip() and not line.startswith("#")]


def _admet_prefilter(job_id: str, smiles_list: list[str], min_qed: float, max_count: int) -> list[str]:
    """Run ADMET Tier 1 and keep GREEN/AMBER molecules."""
    module = AdmetModule()
    result = module.execute(AdmetInput(
        job_id=f"{job_id}_prefilter", smiles_list=smiles_list,
    ))

    if result.status != "completed":
        return smiles_list  # fail open

    profiles = result.data.get("profiles", [])
    passing = [
        p for p in profiles
        if p["overall"] in ("GREEN", "AMBER") and p["tier1"]["qed"] >= min_qed
    ]

    # Sort by QED descending, take top max_count
    passing.sort(key=lambda p: p["tier1"]["qed"], reverse=True)
    return [p["smiles"] for p in passing[:max_count]]


def _run_docking(job_id: str, pdb_path: str, smiles_list: list[str], config: PipelineConfig) -> list[dict]:
    """Run molecular docking."""
    module = DockingModule()
    result = module.execute(DockingInput(
        job_id=f"{job_id}_docking",
        pdb_path=pdb_path,
        smiles_list=smiles_list,
        binding_site=config.binding_site,
        exhaustiveness=config.docking_exhaustiveness,
    ))

    if result.status != "completed":
        return []

    return result.data.get("results", [])


def _run_admet_tier2(job_id: str, smiles_list: list[str]) -> dict[str, dict]:
    """Run ADMET on top candidates and return profiles keyed by SMILES."""
    module = AdmetModule()
    result = module.execute(AdmetInput(
        job_id=f"{job_id}_admet2", smiles_list=smiles_list,
    ))

    if result.status != "completed":
        return {}

    return {p["smiles"]: p for p in result.data.get("profiles", [])}


def _rank_candidates(docking_results: list[dict], admet_profiles: dict[str, dict]) -> list[dict]:
    """Compute composite score and rank candidates."""
    if not docking_results:
        return []

    # Normalise docking scores (more negative = better)
    affinities = [r["best_affinity_kcal_mol"] for r in docking_results]
    min_aff = min(affinities)
    max_aff = max(affinities)
    aff_range = max_aff - min_aff if max_aff != min_aff else 1.0

    ranked = []
    for r in docking_results:
        smiles = r["smiles"]
        admet = admet_profiles.get(smiles, {})
        tier1 = admet.get("tier1", {})

        # Normalised affinity (0-1, higher = better binder)
        norm_aff = (max_aff - r["best_affinity_kcal_mol"]) / aff_range

        qed = tier1.get("qed", 0.5)
        lipinski = 1.0 if tier1.get("lipinski_pass", False) else 0.0
        no_pains = 0.0 if tier1.get("has_pains", True) else 1.0

        composite = (norm_aff * 0.6) + (qed * 0.25) + (lipinski * 0.1) + (no_pains * 0.05)

        ranked.append({
            "rank": 0,
            "smiles": smiles,
            "composite_score": round(composite, 4),
            "docking_affinity_kcal_mol": r["best_affinity_kcal_mol"],
            "admet": admet,
            "overall_flag": admet.get("overall", "AMBER"),
            "pose_3d_path": r.get("pose_pdbqt_path"),
        })

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, c in enumerate(ranked, 1):
        c["rank"] = i

    return ranked


def _fail(job_id: str, message: str) -> dict:
    """Return a failed pipeline result."""
    _progress(job_id, "ranking", 100, message, status="failed")
    return {"error": message, "pipeline_summary": None, "ranked_candidates": []}
