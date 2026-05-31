import { useEffect, useRef, useState } from 'react'
import type { AnalysisUpdate } from './types'
import { cancelAnalysis, openAnalysisStream } from './api'

const ANALYSIS_TIMEOUT_MS = 5 * 60 * 1000

export function useAnalysis(fen: string | null) {
  const [update, setUpdate] = useState<AnalysisUpdate | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const sessionRef = useRef<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const startedAtRef = useRef<number>(0)

  useEffect(() => {
    if (!running) {
      return
    }
    const interval = window.setInterval(() => setTick((value) => value + 1), 1000)
    return () => window.clearInterval(interval)
  }, [running])

  useEffect(() => {
    if (!fen) {
      setUpdate(null)
      setRunning(false)
      return
    }

    const session = crypto.randomUUID()
    sessionRef.current = session
    setUpdate(null)
    setError(null)
    setRunning(true)
    startedAtRef.current = Date.now()

    const source = openAnalysisStream(
      fen,
      session,
      (payload) => setUpdate(payload),
      () => setRunning(false),
      (message) => {
        setError(message)
        setRunning(false)
      },
    )
    sourceRef.current = source

    const timeout = window.setTimeout(() => {
      void cancelAnalysis(session)
      source.close()
      setRunning(false)
    }, ANALYSIS_TIMEOUT_MS)

    return () => {
      window.clearTimeout(timeout)
      source.close()
      if (sessionRef.current) {
        void cancelAnalysis(sessionRef.current)
      }
      setRunning(false)
    }
  }, [fen])

  const elapsedMs =
    update?.elapsed_ms ??
    (running ? Date.now() - startedAtRef.current : 0)
  void tick

  return { update, running, error, elapsedMs }
}
