from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

from modules.base import ModuleInput


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobCreate(BaseModel):
    job_type: str
    input_data: dict[str, Any]
    user_id: str | None = None


class JobRead(BaseModel):
    id: uuid.UUID
    user_id: str | None
    status: str
    job_type: str
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    status: str
    output_data: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Target lookup
# ---------------------------------------------------------------------------

class TargetLookupRequest(BaseModel):
    query: str  # PDB ID, UniProt accession, or protein name
    user_id: str | None = None


class TargetLookupResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# AI query
# ---------------------------------------------------------------------------

class AIQueryInput(ModuleInput):
    query: str
    max_targets: int = 5


class TargetSuggestion(BaseModel):
    protein_name: str
    gene_symbol: str
    uniprot_id: str | None = None
    full_name: str
    confidence: Literal["high", "medium", "low"]
    mechanism_summary: str
    druggability_note: str
    tags: list[str] = []
    has_pdb_structure: bool
    clinical_stage: Literal["approved", "phase3_trials", "preclinical", "unknown"]
    difficulty: Literal["easy", "moderate", "difficult"]


class AIQueryRequest(BaseModel):
    query: str
    max_targets: int = Field(default=5, ge=1, le=8)
    user_id: str | None = None


class AIQueryResponse(BaseModel):
    targets: list[TargetSuggestion]
    query_interpretation: str
    confidence_explanation: str


# ---------------------------------------------------------------------------
# Structure prediction
# ---------------------------------------------------------------------------

class StructurePredictRequest(BaseModel):
    sequence: str
    method: str = "esmfold"  # "esmfold" | "alphafold"
    job_id: str | None = None
    user_id: str | None = None


class StructurePredictResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Docking
# ---------------------------------------------------------------------------

class DockingResult(BaseModel):
    smiles: str
    binding_affinity: float  # kcal/mol
    rmsd: float | None = None
    rank: int


class DockingRequest(BaseModel):
    target_pdb_path: str
    molecules: list[str]  # SMILES strings
    job_id: str | None = None
    user_id: str | None = None


class DockingResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# ADMET
# ---------------------------------------------------------------------------

class AdmetProfile(BaseModel):
    smiles: str
    assay_type: str = "admet"
    mw: float | None = None
    logp: float | None = None
    hbd: int | None = None   # H-bond donors
    hba: int | None = None   # H-bond acceptors
    tpsa: float | None = None
    lipinski_pass: bool | None = None
    bbb_penetrant: bool | None = None
    oral_bioavailability: float | None = None
    toxicity_flags: list[str] = []


class AdmetRequest(BaseModel):
    smiles_list: list[str]
    assay_type: str = "admet"
    job_id: str | None = None
    user_id: str | None = None


class AdmetResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class MoleculeInput(BaseModel):
    smiles: list[str] | None = None
    sdf_base64: str | None = None
    use_zinc_subset: bool = False


class PipelineRequest(BaseModel):
    target_pdb_path: str | None = None
    target_query: str | None = None
    task_type: str  # "virtual_screening" | "protein_design" | "de_novo_generation"
    molecules: MoleculeInput | None = None
    user_id: str | None = None


class PipelineResponse(BaseModel):
    job_id: str
    status: str
