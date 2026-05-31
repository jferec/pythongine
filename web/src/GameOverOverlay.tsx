import { Box, Button, Fade, Typography } from '@mui/material'

export interface GameOverOverlayProps {
  result: 'win' | 'loss' | 'draw'
  reason: string
  onNewGame: () => void
}

const HEADLINES = {
  win: 'You win!',
  loss: 'You lose',
  draw: 'Draw',
} as const

export default function GameOverOverlay({ result, reason, onNewGame }: GameOverOverlayProps) {
  return (
    <Fade in timeout={500}>
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'rgba(0, 0, 0, 0.55)',
          zIndex: 10,
          borderRadius: 1,
        }}
      >
        <Box
          sx={{
            bgcolor: 'background.paper',
            borderRadius: 2,
            px: 4,
            py: 3,
            textAlign: 'center',
            animation: 'scaleIn 0.45s ease-out',
            '@keyframes scaleIn': {
              from: { transform: 'scale(0.85)', opacity: 0 },
              to: { transform: 'scale(1)', opacity: 1 },
            },
          }}
        >
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
            {HEADLINES[result]}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {reason}
          </Typography>
          <Button variant="contained" onClick={onNewGame}>
            New game
          </Button>
        </Box>
      </Box>
    </Fade>
  )
}
