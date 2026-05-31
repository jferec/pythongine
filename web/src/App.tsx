import { Box, Tab, Tabs, Typography } from '@mui/material'
import { useState } from 'react'
import PlayView from './PlayView'
import ReviewView from './ReviewView'

export default function App() {
  const [tab, setTab] = useState(0)

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        Pythongine
      </Typography>
      <Tabs value={tab} onChange={(_event, value: number) => setTab(value)} sx={{ mb: 3 }}>
        <Tab label="Review" />
        <Tab label="Play" />
      </Tabs>
      {tab === 0 && <ReviewView />}
      {tab === 1 && <PlayView />}
    </Box>
  )
}
