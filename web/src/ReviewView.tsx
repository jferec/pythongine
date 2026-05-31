import {
  Box,
  Button,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import {
  FirstPage,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  LastPage,
} from '@mui/icons-material'
import { Chessboard } from 'react-chessboard'
import { useState } from 'react'
import {
  fetchStaticEval,
  formatElapsed,
  formatScore,
  loadLichessGame,
} from './api'
import type { LoadedGame } from './types'
import { useAnalysis } from './useAnalysis'

function fenAtPly(game: LoadedGame, ply: number): string {
  if (ply <= 0) {
    return game.start_fen
  }
  return game.moves[ply - 1]?.fen ?? game.start_fen
}

function boardOrientation(fen: string): 'white' | 'black' {
  return fen.split(' ')[1] === 'b' ? 'black' : 'white'
}

export default function ReviewView() {
  const [urlInput, setUrlInput] = useState('')
  const [game, setGame] = useState<LoadedGame | null>(null)
  const [ply, setPly] = useState(0)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [staticEval, setStaticEval] = useState<number | null>(null)

  const currentFen = game ? fenAtPly(game, ply) : null
  const { update, running, error: analysisError, elapsedMs, logs } = useAnalysis(currentFen)

  async function handleLoad() {
    setLoading(true)
    setLoadError(null)
    try {
      const loaded = await loadLichessGame(urlInput.trim())
      setGame(loaded)
      setPly(0)
      const evalScore = await fetchStaticEval(loaded.start_fen)
      setStaticEval(evalScore)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load game')
    } finally {
      setLoading(false)
    }
  }

  async function goToPly(nextPly: number) {
    if (!game) {
      return
    }
    const clamped = Math.max(0, Math.min(nextPly, game.moves.length))
    setPly(clamped)
    const fen = fenAtPly(game, clamped)
    try {
      setStaticEval(await fetchStaticEval(fen))
    } catch {
      setStaticEval(null)
    }
  }

  const displayEval = update?.static_eval ?? staticEval
  const topMoves = update?.top_moves ?? []

  return (
    <>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 3 }}>
        <TextField
          fullWidth
          label="Lichess URL or game ID"
          value={urlInput}
          onChange={(event) => setUrlInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              void handleLoad()
            }
          }}
        />
        <Button variant="contained" onClick={() => void handleLoad()} disabled={loading || !urlInput.trim()}>
          Load
        </Button>
      </Stack>

      {loadError && (
        <Typography color="error" sx={{ mb: 2 }}>
          {loadError}
        </Typography>
      )}

      {game && (
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
          <Chip label={`${game.headers.White ?? '?'} vs ${game.headers.Black ?? '?'}`} />
          {game.headers.ECO && <Chip label={game.headers.ECO} variant="outlined" />}
          {game.headers.Event && <Chip label={game.headers.Event} variant="outlined" />}
        </Stack>
      )}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ width: '100%', maxWidth: 520, mx: 'auto' }}>
              {currentFen ? (
                <Chessboard
                  options={{
                    position: currentFen.split(' ')[0],
                    boardOrientation: boardOrientation(currentFen),
                    allowDragging: false,
                    darkSquareStyle: { backgroundColor: '#b58863' },
                    lightSquareStyle: { backgroundColor: '#f0d9b5' },
                  }}
                />
              ) : (
                <Box
                  sx={{
                    aspectRatio: '1',
                    bgcolor: 'grey.100',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Typography color="text.secondary">Load a Lichess game to begin</Typography>
                </Box>
              )}
            </Box>

            <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center' }}>
              <Button onClick={() => void goToPly(0)} disabled={!game}>
                <FirstPage />
              </Button>
              <Button onClick={() => void goToPly(ply - 1)} disabled={!game || ply === 0}>
                <KeyboardArrowLeft />
              </Button>
              <Typography sx={{ alignSelf: 'center', minWidth: 96, textAlign: 'center' }}>
                ply {ply}{game ? ` / ${game.moves.length}` : ''}
              </Typography>
              <Button
                onClick={() => void goToPly(ply + 1)}
                disabled={!game || ply >= (game?.moves.length ?? 0)}
              >
                <KeyboardArrowRight />
              </Button>
              <Button
                onClick={() => void goToPly(game?.moves.length ?? 0)}
                disabled={!game || ply >= (game?.moves.length ?? 0)}
              >
                <LastPage />
              </Button>
            </Stack>

            <Box sx={{ mt: 2, maxHeight: 180, overflow: 'auto' }}>
              {game?.moves.map((move) => (
                <Typography
                  key={move.ply}
                  component="span"
                  variant="body2"
                  sx={{
                    cursor: 'pointer',
                    fontWeight: move.ply === ply ? 700 : 400,
                    mr: move.ply % 2 === 0 ? 1 : 0.5,
                  }}
                  onClick={() => void goToPly(move.ply)}
                >
                  {move.ply % 2 === 1 ? `${Math.ceil(move.ply / 2)}. ${move.san}` : move.san}
                  {move.ply % 2 === 1 && move.ply !== (game?.moves.length ?? 0) ? ' ' : move.ply % 2 === 0 ? ' ' : ''}
                </Typography>
              ))}
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 2, minHeight: 420 }}>
            <Typography variant="h6" gutterBottom>
              Engine
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              Static eval: {displayEval !== null ? formatScore(displayEval) : '—'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Depth: {update?.depth ?? 0} ({formatElapsed(elapsedMs)} / 5:00)
            </Typography>
            {running && <LinearProgress sx={{ mb: 2 }} />}
            {analysisError && (
              <Typography color="error" sx={{ mb: 2 }}>
                {analysisError}
              </Typography>
            )}

            {logs.length > 0 && (
              <Box
                sx={{
                  mb: 2,
                  maxHeight: 120,
                  overflow: 'auto',
                  bgcolor: 'grey.50',
                  borderRadius: 1,
                  p: 1,
                  fontFamily: 'monospace',
                  fontSize: 12,
                }}
              >
                {logs.map((line, index) => (
                  <Typography
                    key={`${index}-${line}`}
                    variant="caption"
                    component="div"
                    sx={{ display: 'block' }}
                  >
                    {line}
                  </Typography>
                ))}
              </Box>
            )}

            <Stack spacing={1}>
              {topMoves.map((move, index) => (
                <Box
                  key={`${move.san}-${index}`}
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: '24px 56px 64px 1fr',
                    gap: 1,
                    alignItems: 'center',
                  }}
                >
                  <Typography variant="body2">{index + 1}.</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {move.san}
                  </Typography>
                  <Typography variant="body2">{formatScore(move.score_cp)}</Typography>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {move.pv.slice(1, 4).join(' ')}
                  </Typography>
                </Box>
              ))}
              {!topMoves.length && (
                <Typography variant="body2" color="text.secondary">
                  {currentFen ? 'Searching…' : 'No analysis yet'}
                </Typography>
              )}
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </>
  )
}
