import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from '@mui/material'

export interface PromotionDialogProps {
  open: boolean
  onPick: (piece: 'Q' | 'R' | 'B' | 'N') => void
  onCancel: () => void
}

const OPTIONS = [
  { label: 'Queen', value: 'Q' as const },
  { label: 'Rook', value: 'R' as const },
  { label: 'Bishop', value: 'B' as const },
  { label: 'Knight', value: 'N' as const },
]

export default function PromotionDialog({ open, onPick, onCancel }: PromotionDialogProps) {
  return (
    <Dialog open={open} onClose={onCancel}>
      <DialogTitle>Promote pawn to</DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={1} sx={{ pt: 1 }}>
          {OPTIONS.map((option) => (
            <Button key={option.value} variant="outlined" onClick={() => onPick(option.value)}>
              {option.label}
            </Button>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
      </DialogActions>
    </Dialog>
  )
}
