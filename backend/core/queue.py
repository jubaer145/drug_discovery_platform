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


@celery_app.task(name="tasks.run_target_lookup")
def run_target_lookup(job_id: str, query: str, user_id: str | None = None) -> dict:
    """Placeholder — implemented in Sprint 1."""
    raise NotImplementedError("run_target_lookup not yet implemented")


@celery_app.task(name="tasks.run_ai_query")
def run_ai_query(job_id: str, disease_description: str, user_id: str | None = None) -> dict:
    """Placeholder — implemented in Sprint 2."""
    raise NotImplementedError("run_ai_query not yet implemented")


@celery_app.task(name="tasks.run_structure_prediction")
def run_structure_prediction(job_id: str, sequence: str, method: str = "esmfold") -> dict:
    """Placeholder — implemented in Sprint 3."""
    raise NotImplementedError("run_structure_prediction not yet implemented")


@celery_app.task(name="tasks.run_docking")
def run_docking(job_id: str, target_pdb_path: str, smiles_list: list) -> dict:
    """Placeholder — implemented in Sprint 4."""
    raise NotImplementedError("run_docking not yet implemented")


@celery_app.task(name="tasks.run_admet")
def run_admet(job_id: str, smiles_list: list) -> dict:
    """Placeholder — implemented in Sprint 5."""
    raise NotImplementedError("run_admet not yet implemented")


@celery_app.task(name="tasks.run_pipeline")
def run_pipeline(job_id: str, pipeline_config: dict) -> dict:
    """Placeholder — implemented in Sprint 6."""
    raise NotImplementedError("run_pipeline not yet implemented")
