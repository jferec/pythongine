export interface MoveRecord {
  ply: number
  san: string
  fen: string
}

export interface LoadedGame {
  id: string
  lichess_id: string
  headers: Record<string, string>
  start_fen: string
  moves: MoveRecord[]
}

export interface ScoredMove {
  san: string
  score_cp: number
  depth: number
  pv: string[]
}

export interface AnalysisUpdate {
  depth: number
  static_eval: number
  elapsed_ms: number
  top_moves: ScoredMove[]
}
