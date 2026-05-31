import type { AnalysisUpdate, LoadedGame } from './types'

export async function loadLichessGame(urlOrId: string): Promise<LoadedGame> {
  const response = await fetch('/api/games/lichess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url_or_id: urlOrId }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Failed to load game (${response.status})`)
  }
  return response.json()
}

export async function fetchStaticEval(fen: string): Promise<number> {
  const response = await fetch(`/api/position/eval?fen=${encodeURIComponent(fen)}`)
  if (!response.ok) {
    throw new Error('Failed to fetch static eval')
  }
  const body = await response.json()
  return body.static_eval
}

export async function cancelAnalysis(session: string): Promise<void> {
  await fetch('/api/analyze/cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session }),
  })
}

export function openAnalysisStream(
  fen: string,
  session: string,
  onUpdate: (update: AnalysisUpdate) => void,
  onDone: () => void,
  onError: (message: string) => void,
): EventSource {
  const source = new EventSource(
    `/api/analyze?fen=${encodeURIComponent(fen)}&session=${encodeURIComponent(session)}`,
  )

  source.addEventListener('update', (event) => {
    onUpdate(JSON.parse(event.data) as AnalysisUpdate)
  })

  source.addEventListener('done', () => {
    source.close()
    onDone()
  })

  source.addEventListener('cancelled', () => {
    source.close()
    onDone()
  })

  source.addEventListener('error', () => {
    if (source.readyState === EventSource.CLOSED) {
      return
    }
    source.close()
    onError('Analysis stream disconnected')
  })

  return source
}

export function formatScore(scoreCp: number): string {
  if (Math.abs(scoreCp) >= 29000) {
    const mateIn = Math.ceil((30000 - Math.abs(scoreCp)) / 2)
    return scoreCp > 0 ? `#${mateIn}` : `#-${mateIn}`
  }
  const pawns = scoreCp / 100
  return pawns > 0 ? `+${pawns.toFixed(2)}` : pawns.toFixed(2)
}

export function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}
