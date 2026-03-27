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

class TargetLookupInput(ModuleInput):
    query: str
    query_type: Literal["pdb_id", "uniprot", "name", "auto"] = "auto"


class TargetLookupRequest(BaseModel):
    query: str  # PDB ID, UniProt accession, or protein name
    user_id: str | None = None


class PDBStructureInfo(BaseModel):
    pdb_id: str
    resolution: float | None = None
    method: str | None = None
    has_ligand: bool = False
    ligand_name: str | None = None


class TargetLookupResult(BaseModel):
    protein_name: str
    gene_symbol: str | None = None
    uniprot_id: str | None = None
    organism: str | None = None
    sequence_length: int | None = None
    sequence: str | None = None
    function_summary: str | None = None
    disease_associations: list[str] = []
    pdb_structures: list[PDBStructureInfo] = []
    best_pdb_id: str | None = None
    total_pdb_count: int = 0
    has_alphafold: bool = False
    alphafold_url: str | None = None
    multiple_candidates: list[dict[str, Any]] | None = None


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

class StructurePredInput(ModuleInput):
    sequence: str
    sequence_name: str = ""
    force_predict: bool = False


class StructurePredictRequest(BaseModel):
    sequence: str
    method: str = "esmfold"  # "esmfold" | "alphafold"
    sequence_name: str = ""
    user_id: str | None = None


class StructurePredictResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Docking
# ---------------------------------------------------------------------------

class DockingInput(ModuleInput):
    pdb_path: str
    smiles_list: list[str]
    binding_site: dict[str, float] | None = None
    exhaustiveness: int = 8
    num_poses: int = 3


class DockingResult(BaseModel):
    smiles: str
    rank: int
    best_affinity_kcal_mol: float
    all_pose_affinities: list[float] = []
    pose_pdbqt_path: str | None = None
    docking_success: bool = True


class DockingRequest(BaseModel):
    target_pdb_path: str
    molecules: list[str]  # SMILES strings
    binding_site: dict[str, float] | None = None
    exhaustiveness: int = 8
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
