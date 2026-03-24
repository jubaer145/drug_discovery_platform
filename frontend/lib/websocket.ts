const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000'

export interface JobProgressMessage {
  job_id: string
  status: string
  progress?: number
  message?: string
  data?: Record<string, unknown>
}

export function createJobSocket(
  jobId: string,
  onMessage: (msg: JobProgressMessage) => void,
  onError?: (err: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_URL}/ws/jobs/${jobId}`)

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data as string) as JobProgressMessage
      onMessage(msg)
    } catch {
      console.error('Failed to parse WebSocket message', event.data)
    }
  }

  if (onError) {
    ws.onerror = onError
  }

  return ws
}
