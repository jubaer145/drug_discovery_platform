// ---------------------------------------------------------------------------
// Job
// ---------------------------------------------------------------------------

export interface Job {
  id: string
  user_id: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  job_type: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown> | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface JobCreate {
  job_type: string
  input_data: Record<string, unknown>
  user_id?: string
}

export interface JobStatusUpdate {
  status: string
  output_data?: Record<string, unknown>
  error?: string
}

// ---------------------------------------------------------------------------
// Target lookup
// ---------------------------------------------------------------------------

export interface TargetLookupRequest {
  query: string
  user_id?: string
}

export interface TargetLookupResponse {
  job_id: string
  status: string
}

// ---------------------------------------------------------------------------
// AI query
// ---------------------------------------------------------------------------

export interface TargetSuggestion {
  protein_name: string
  gene_symbol: string
  uniprot_id: string | null
  full_name: string
  confidence: 'high' | 'medium' | 'low'
  mechanism_summary: string
  druggability_note: string
  tags: string[]
  has_pdb_structure: boolean
  clinical_stage: 'approved' | 'phase3_trials' | 'preclinical' | 'unknown'
  difficulty: 'easy' | 'moderate' | 'difficult'
}

export interface AIQueryRequest {
  query: string
  max_targets?: number
  user_id?: string
}

export interface AIQueryResponse {
  targets: TargetSuggestion[]
  query_interpretation: string
  confidence_explanation: string
}

// ---------------------------------------------------------------------------
// Structure prediction
// ---------------------------------------------------------------------------

export interface StructurePredictRequest {
  sequence: string
  method?: 'esmfold' | 'alphafold'
  job_id?: string
  user_id?: string
}

export interface StructurePredictResponse {
  job_id: string
  status: string
}

// ---------------------------------------------------------------------------
// Docking
// ---------------------------------------------------------------------------

export interface DockingResult {
  smiles: string
  binding_affinity: number
  rmsd: number | null
  rank: number
}

export interface DockingRequest {
  target_pdb_path: string
  molecules: string[]
  job_id?: string
  user_id?: string
}

export interface DockingResponse {
  job_id: string
  status: string
}

// ---------------------------------------------------------------------------
// ADMET
// ---------------------------------------------------------------------------

export interface AdmetProfile {
  smiles: string
  assay_type: string
  mw: number | null
  logp: number | null
  hbd: number | null
  hba: number | null
  tpsa: number | null
  lipinski_pass: boolean | null
  bbb_penetrant: boolean | null
  oral_bioavailability: number | null
  toxicity_flags: string[]
}

export interface AdmetRequest {
  smiles_list: string[]
  assay_type?: string
  job_id?: string
  user_id?: string
}

export interface AdmetResponse {
  job_id: string
  status: string
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------

export interface MoleculeInput {
  smiles?: string[]
  sdf_base64?: string
  use_zinc_subset?: boolean
}

export interface PipelineRequest {
  target_pdb_path?: string
  target_query?: string
  task_type: 'virtual_screening' | 'protein_design' | 'de_novo_generation'
  molecules?: MoleculeInput
  user_id?: string
}

export interface PipelineResponse {
  job_id: string
  status: string
}
