export type PlayerColor = 'white' | 'black'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type PlayerResult = 'win' | 'loss' | 'draw'

export interface LegalMove {
  from: string
  to: string
  san: string
  promotion: string | null
}

export interface MoveRecord {
  ply: number
  san: string
  fen: string
}

export interface PlayMoveResponse {
  san: string
  fen: string
  status: 'ongoing' | 'checkmate' | 'stalemate'
  player_result: PlayerResult | null
  score_cp?: number
  depth?: number
}

export const START_FEN =
  'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

export const THINK_MS: Record<Difficulty, number> = {
  easy: 15_000,
  medium: 60_000,
  hard: 180_000,
}

export async function fetchLegalMoves(fen: string): Promise<LegalMove[]> {
  const response = await fetch(`/api/play/legal-moves?fen=${encodeURIComponent(fen)}`)
  if (!response.ok) {
    throw new Error('Failed to fetch legal moves')
  }
  const body = await response.json()
  return body.moves
}

export async function applyMove(
  fen: string,
  from: string,
  to: string,
  playerColor: PlayerColor,
  promotion?: string,
): Promise<PlayMoveResponse> {
  const response = await fetch('/api/play/apply-move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fen,
      from,
      to,
      promotion: promotion ?? null,
      player_color: playerColor,
    }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Illegal move')
  }
  return response.json()
}

export async function requestEngineMove(
  fen: string,
  thinkMs: number,
  playerColor: PlayerColor,
): Promise<PlayMoveResponse> {
  const response = await fetch('/api/play/engine-move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fen,
      think_ms: thinkMs,
      player_color: playerColor,
    }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Engine move failed')
  }
  return response.json()
}

export function findMatchingMoves(
  legalMoves: LegalMove[],
  from: string,
  to: string,
): LegalMove[] {
  return legalMoves.filter((move) => move.from === from && move.to === to)
}

export function sideToMove(fen: string): PlayerColor {
  return fen.split(' ')[1] === 'b' ? 'black' : 'white'
}
