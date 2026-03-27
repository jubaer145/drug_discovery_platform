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

export interface JobProgressUpdate {
  job_id: string
  status: string
  step: string
  progress_pct: number
  message: string
  completed_steps: string[]
  current_step: string
  pending_steps: string[]
  timestamp: string
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
  sequence_name?: string
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
  rank: number
  best_affinity_kcal_mol: number
  all_pose_affinities: number[]
  pose_pdbqt_path: string | null
  docking_success: boolean
}

export interface DockingRequest {
  target_pdb_path: string
  molecules: string[]
  binding_site?: Record<string, number>
  exhaustiveness?: number
  user_id?: string
}

export interface DockingResponse {
  job_id: string
  status: string
}

// ---------------------------------------------------------------------------
// ADMET
// ---------------------------------------------------------------------------

export interface AdmetTier1 {
  mw: number
  logp: number
  hbd: number
  hba: number
  tpsa: number
  rot_bonds: number
  qed: number
  lipinski_pass: boolean
  lipinski_violations: string[]
  has_pains: boolean
  sa_score: number
}

export interface AdmetProfile {
  smiles: string
  overall: 'GREEN' | 'AMBER' | 'RED'
  recommendation: 'recommended' | 'investigate' | 'not_recommended'
  tier1: AdmetTier1
  tier2: Record<string, unknown> | null
  flags: Array<{ type: string; message: string }>
}

export interface AdmetRequest {
  smiles_list: string[]
  run_tier2?: boolean
  user_id?: string
}

export interface AdmetResponse {
  job_id: string
  status: string
  total?: number
  profiles?: AdmetProfile[]
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
  target_pdb_id?: string
  target_uniprot_id?: string
  target_sequence?: string
  target_query?: string
  task_type: 'virtual_screening' | 'protein_design' | 'de_novo_generation'
  molecules?: MoleculeInput
  binding_site?: Record<string, number>
  admet_filter_before_docking?: boolean
  docking_exhaustiveness?: number
  max_molecules_to_dock?: number
  user_id?: string
}

export interface RankedCandidate {
  rank: number
  smiles: string
  composite_score: number
  docking_affinity_kcal_mol: number
  admet: AdmetProfile
  overall_flag: 'GREEN' | 'AMBER' | 'RED'
  pose_3d_path: string | null
  next_step_suggestion?: string
}

export interface PipelineResult {
  pipeline_summary: {
    total_input_molecules: number
    after_admet_prefilter: number
    successfully_docked: number
    top_candidates: number
  }
  target: Record<string, unknown>
  ranked_candidates: RankedCandidate[]
  structure_used: {
    source: string
    pdb_id?: string
    resolution?: number
  }
  binding_site: Record<string, number> | null
}

export interface PipelineResponse {
  job_id: string
  status: string
  estimated_minutes?: number
}
