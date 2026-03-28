from celery import Celery
from .config import settings

celery_app = Celery(
    "drug_discovery",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
)


def _progress(job_id: str, step: str, pct: int, msg: str, **kwargs):
    """Helper to emit progress updates from Celery tasks."""
    from core.websocket import send_progress_update
    send_progress_update(job_id, step, pct, msg, **kwargs)


@celery_app.task(name="tasks.run_target_lookup")
def run_target_lookup(job_id: str, query: str, user_id: str | None = None) -> dict:
    """Look up a protein target by PDB ID, UniProt accession, or name."""
    from modules.target_lookup import TargetLookupModule
    from models.schemas import TargetLookupInput

    _progress(job_id, "target_lookup", 10, "Starting target lookup...",
              pending_steps=["target_lookup"])

    module = TargetLookupModule()
    module_input = TargetLookupInput(job_id=job_id, user_id=user_id, query=query)
    result = module.execute(module_input)

    _progress(job_id, "target_lookup", 100, "Target lookup complete",
              status="completed" if result.status == "completed" else "failed",
              completed_steps=["target_lookup"])

    return result.model_dump()


@celery_app.task(name="tasks.run_ai_query")
def run_ai_query(job_id: str, disease_description: str, user_id: str | None = None) -> dict:
    """Placeholder — AI query runs synchronously via route."""
    raise NotImplementedError("run_ai_query not yet implemented")


@celery_app.task(name="tasks.run_structure_prediction", bind=True, max_retries=1, time_limit=300)
def run_structure_prediction(self, job_id: str, sequence: str, sequence_name: str = "") -> dict:
    """Predict 3D protein structure via ESMFold API."""
    from modules.structure_pred import StructurePredModule
    from models.schemas import StructurePredInput

    _progress(job_id, "structure_prediction", 10, "Submitting sequence to ESMFold...",
              pending_steps=["structure_prediction"])

    module = StructurePredModule()
    module_input = StructurePredInput(job_id=job_id, sequence=sequence, sequence_name=sequence_name)
    result = module.execute(module_input)

    _progress(job_id, "structure_prediction", 100, "Structure prediction complete",
              status="completed" if result.status == "completed" else "failed",
              completed_steps=["structure_prediction"])

    return result.model_dump()


@celery_app.task(name="tasks.run_docking", bind=True, max_retries=0, time_limit=3600)
def run_docking(self, job_id: str, input_data: dict) -> dict:
    """Dock molecules against a protein structure using AutoDock Vina."""
    from modules.docking import DockingModule
    from models.schemas import DockingInput

    _progress(job_id, "docking", 5, "Preparing receptor...",
              pending_steps=["docking", "ranking"])

    module = DockingModule()
    module_input = DockingInput(job_id=job_id, **input_data)
    result = module.execute(module_input)

    _progress(job_id, "docking", 100, "Docking complete",
              status="completed" if result.status == "completed" else "failed",
              completed_steps=["docking"])

    return result.model_dump()


@celery_app.task(name="tasks.run_admet")
def run_admet(job_id: str, smiles_list: list, run_tier2: bool = False) -> dict:
    """Predict ADMET properties for a list of SMILES."""
    from modules.admet import AdmetModule
    from models.schemas import AdmetInput

    _progress(job_id, "admet", 10, "Running ADMET Tier 1 analysis...",
              pending_steps=["admet"])

    module = AdmetModule()
    module_input = AdmetInput(job_id=job_id, smiles_list=smiles_list, run_tier2=run_tier2)
    result = module.execute(module_input)

    _progress(job_id, "admet", 100, "ADMET prediction complete",
              status="completed" if result.status == "completed" else "failed",
              completed_steps=["admet"])

    return result.model_dump()


@celery_app.task(name="tasks.run_pipeline_task", bind=True, max_retries=0, time_limit=7200)
def run_pipeline_task(self, job_id: str, config_data: dict) -> dict:
    """Run the full pipeline orchestrator."""
    from core.pipeline import run_virtual_screening
    from models.schemas import PipelineConfig

    config = PipelineConfig(job_id=job_id, **config_data)

    if config.task == "virtual_screening":
        return run_virtual_screening(job_id, config)

    return {"error": f"Task type '{config.task}' not yet implemented"}
