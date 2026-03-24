import type {
  Job,
  AIQueryRequest,
  AIQueryResponse,
  TargetLookupRequest,
  TargetLookupResponse,
  StructurePredictRequest,
  StructurePredictResponse,
  DockingRequest,
  DockingResponse,
  AdmetRequest,
  AdmetResponse,
  PipelineRequest,
  PipelineResponse,
} from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.text()
    throw new Error(`API error ${res.status}: ${error}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    request<{ status: string; version: string }>('/health'),

  jobs: {
    get: (jobId: string) =>
      request<Job>(`/api/jobs/${jobId}`),
  },

  ai: {
    suggestTargets: (body: AIQueryRequest) =>
      request<AIQueryResponse>('/api/ai/suggest-targets', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },

  targets: {
    lookup: (body: TargetLookupRequest) =>
      request<TargetLookupResponse>('/api/targets/lookup', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },

  structures: {
    predict: (body: StructurePredictRequest) =>
      request<StructurePredictResponse>('/api/structures/predict', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },

  docking: {
    run: (body: DockingRequest) =>
      request<DockingResponse>('/api/docking/run', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },

  admet: {
    predict: (body: AdmetRequest) =>
      request<AdmetResponse>('/api/admet/predict', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },

  pipeline: {
    run: (body: PipelineRequest) =>
      request<PipelineResponse>('/api/pipeline/run', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
}
