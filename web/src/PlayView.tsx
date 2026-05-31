import {
  Box,
  Button,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
} from '@mui/material'
import { Chessboard } from 'react-chessboard'
import { useCallback, useEffect, useRef, useState } from 'react'
import { formatElapsed } from './api'
import GameOverOverlay from './GameOverOverlay'
import PromotionDialog from './PromotionDialog'
import {
  START_FEN,
  THINK_MS,
  applyMove,
  fetchLegalMoves,
  findMatchingMoves,
  requestEngineMove,
  sideToMove,
  type Difficulty,
  type LegalMove,
  type MoveRecord,
  type PlayerColor,
  type PlayerResult,
} from './playApi'

const BOARD_OPTIONS = {
  darkSquareStyle: { backgroundColor: '#b58863' },
  lightSquareStyle: { backgroundColor: '#f0d9b5' },
}

interface PendingPromotion {
  from: string
  to: string
}

export default function PlayView() {
  const [phase, setPhase] = useState<'setup' | 'playing' | 'finished'>('setup')
  const [playerColor, setPlayerColor] = useState<PlayerColor>('white')
  const [difficulty, setDifficulty] = useState<Difficulty>('easy')
  const [fen, setFen] = useState(START_FEN)
  const [moves, setMoves] = useState<MoveRecord[]>([])
  const [legalMoves, setLegalMoves] = useState<LegalMove[]>([])
  const [engineThinking, setEngineThinking] = useState(false)
  const [engineElapsedMs, setEngineElapsedMs] = useState(0)
  const [gameOver, setGameOver] = useState<{ result: PlayerResult; reason: string } | null>(null)
  const [pendingPromotion, setPendingPromotion] = useState<PendingPromotion | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fenRef = useRef(fen)
  const engineStartedAtRef = useRef(0)
  const thinkMsRef = useRef(THINK_MS.easy)

  fenRef.current = fen

  const refreshLegalMoves = useCallback(async (positionFen: string) => {
    const movesList = await fetchLegalMoves(positionFen)
    setLegalMoves(movesList)
  }, [])

  const finishGame = useCallback((result: PlayerResult, reason: string) => {
    setGameOver({ result, reason })
    setPhase('finished')
    setEngineThinking(false)
  }, [])

  const afterMove = useCallback(
    async (response: { fen: string; san: string; player_result: PlayerResult | null; status: string }) => {
      setFen(response.fen)
      setMoves((current) => [
        ...current,
        { ply: current.length + 1, san: response.san, fen: response.fen },
      ])
      await refreshLegalMoves(response.fen)

      if (response.player_result === 'win') {
        finishGame('win', 'Checkmate')
        return
      }
      if (response.player_result === 'loss') {
        finishGame('loss', 'Checkmate')
        return
      }
      if (response.player_result === 'draw') {
        finishGame('draw', 'Stalemate')
        return
      }
    },
    [finishGame, refreshLegalMoves],
  )

  const runEngineTurn = useCallback(
    async (positionFen: string, color: PlayerColor) => {
      if (sideToMove(positionFen) === color) {
        return
      }
      setEngineThinking(true)
      setEngineElapsedMs(0)
      engineStartedAtRef.current = Date.now()
      try {
        const response = await requestEngineMove(positionFen, thinkMsRef.current, color)
        await afterMove(response)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Engine move failed')
      } finally {
        setEngineThinking(false)
      }
    },
    [afterMove],
  )

  const submitPlayerMove = useCallback(
    async (from: string, to: string, promotion?: string) => {
      setError(null)
      try {
        const response = await applyMove(fenRef.current, from, to, playerColor, promotion)
        await afterMove(response)
        if (response.player_result === null && sideToMove(response.fen) !== playerColor) {
          void runEngineTurn(response.fen, playerColor)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Move failed')
        setFen(fenRef.current)
      }
    },
    [afterMove, playerColor, runEngineTurn],
  )

  const startGame = useCallback(async () => {
    thinkMsRef.current = THINK_MS[difficulty]
    setPhase('playing')
    setFen(START_FEN)
    setMoves([])
    setGameOver(null)
    setError(null)
    setEngineThinking(false)
    await refreshLegalMoves(START_FEN)
    if (playerColor === 'black') {
      void runEngineTurn(START_FEN, playerColor)
    }
  }, [difficulty, playerColor, refreshLegalMoves, runEngineTurn])

  useEffect(() => {
    if (!engineThinking) {
      return
    }
    const interval = window.setInterval(() => {
      setEngineElapsedMs(Date.now() - engineStartedAtRef.current)
    }, 1000)
    return () => window.clearInterval(interval)
  }, [engineThinking])

  const canPlayerMove = phase === 'playing' && !engineThinking && sideToMove(fen) === playerColor

  function handleDrop(sourceSquare: string, targetSquare: string | null): boolean {
    if (!canPlayerMove || !targetSquare) {
      return false
    }
    const matches = findMatchingMoves(legalMoves, sourceSquare, targetSquare)
    if (matches.length === 0) {
      return false
    }
    const promotions = matches.filter((move) => move.promotion !== null)
    if (promotions.length > 1) {
      setPendingPromotion({ from: sourceSquare, to: targetSquare })
      return false
    }
    if (promotions.length === 1) {
      void submitPlayerMove(sourceSquare, targetSquare, promotions[0].promotion ?? 'Q')
      return true
    }
    void submitPlayerMove(sourceSquare, targetSquare)
    return true
  }

  function handlePromotionPick(piece: 'Q' | 'R' | 'B' | 'N') {
    if (!pendingPromotion) {
      return
    }
    void submitPlayerMove(pendingPromotion.from, pendingPromotion.to, piece)
    setPendingPromotion(null)
  }

  if (phase === 'setup') {
    return (
      <Paper sx={{ p: 3, maxWidth: 480 }}>
        <Typography variant="h5" gutterBottom>
          Play vs Engine
        </Typography>
        <Stack spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Your color</InputLabel>
            <Select
              label="Your color"
              value={playerColor}
              onChange={(event) => setPlayerColor(event.target.value as PlayerColor)}
            >
              <MenuItem value="white">White</MenuItem>
              <MenuItem value="black">Black</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Difficulty</InputLabel>
            <Select
              label="Difficulty"
              value={difficulty}
              onChange={(event) => setDifficulty(event.target.value as Difficulty)}
            >
              <MenuItem value="easy">Easy (15s per move)</MenuItem>
              <MenuItem value="medium">Medium (1 min per move)</MenuItem>
              <MenuItem value="hard">Hard (3 min per move)</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" onClick={() => void startGame()}>
            Start game
          </Button>
        </Stack>
      </Paper>
    )
  }

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, md: 7 }}>
        <Paper sx={{ p: 2 }}>
          <Box sx={{ position: 'relative', width: '100%', maxWidth: 520, mx: 'auto' }}>
            <Chessboard
              options={{
                position: fen.split(' ')[0],
                boardOrientation: playerColor,
                allowDragging: canPlayerMove,
                canDragPiece: ({ piece }) =>
                  canPlayerMove &&
                  ((playerColor === 'white' && piece.pieceType.startsWith('w')) ||
                    (playerColor === 'black' && piece.pieceType.startsWith('b'))),
                onPieceDrop: ({ sourceSquare, targetSquare }) =>
                  handleDrop(sourceSquare, targetSquare),
                ...BOARD_OPTIONS,
              }}
            />
            {gameOver && (
              <GameOverOverlay
                result={gameOver.result}
                reason={gameOver.reason}
                onNewGame={() => setPhase('setup')}
              />
            )}
          </Box>
          {engineThinking && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Engine thinking… {formatElapsed(engineElapsedMs)} /{' '}
                {formatElapsed(thinkMsRef.current)}
              </Typography>
              <LinearProgress />
            </Box>
          )}
          {error && (
            <Typography color="error" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}
        </Paper>
      </Grid>
      <Grid size={{ xs: 12, md: 5 }}>
        <Paper sx={{ p: 2, minHeight: 420 }}>
          <Stack direction="row" sx={{ mb: 2, justifyContent: 'space-between' }}>
            <Typography variant="h6">Moves</Typography>
            <Button size="small" onClick={() => setPhase('setup')}>
              New game
            </Button>
          </Stack>
          <Box sx={{ maxHeight: 360, overflow: 'auto' }}>
            {moves.map((move) => (
              <Typography
                key={move.ply}
                component="span"
                variant="body2"
                sx={{ mr: move.ply % 2 === 0 ? 1 : 0.5 }}
              >
                {move.ply % 2 === 1 ? `${Math.ceil(move.ply / 2)}. ${move.san}` : move.san}
                {move.ply % 2 === 1 ? ' ' : ' '}
              </Typography>
            ))}
            {!moves.length && (
              <Typography variant="body2" color="text.secondary">
                No moves yet
              </Typography>
            )}
          </Box>
        </Paper>
      </Grid>
      <PromotionDialog
        open={pendingPromotion !== null}
        onPick={handlePromotionPick}
        onCancel={() => setPendingPromotion(null)}
      />
    </Grid>
  )
}
