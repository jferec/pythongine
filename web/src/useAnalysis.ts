import { useEffect, useRef, useState } from 'react'
import type { AnalysisUpdate } from './types'
import { cancelAnalysis, openAnalysisStream } from './api'

const ANALYSIS_TIMEOUT_MS = 5 * 60 * 1000

export function useAnalysis(fen: string | null) {
  const [update, setUpdate] = useState<AnalysisUpdate | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsedMs, setElapsedMs] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const sessionRef = useRef<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const startedAtRef = useRef<number>(0)

  useEffect(() => {
    if (!running) {
      return
    }
    const interval = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAtRef.current)
    }, 1000)
    return () => window.clearInterval(interval)
  }, [running])

  useEffect(() => {
    if (!fen) {
      setUpdate(null)
      setRunning(false)
      setElapsedMs(0)
      setLogs([])
      return
    }

    const session = crypto.randomUUID()
    sessionRef.current = session
    setUpdate(null)
    setError(null)
    setLogs([])
    setRunning(true)
    startedAtRef.current = Date.now()
    setElapsedMs(0)

    const source = openAnalysisStream(
      fen,
      session,
      (payload) => setUpdate(payload),
      (message) => setLogs((current) => [...current, message]),
      (serverElapsedMs) => setElapsedMs(serverElapsedMs),
      (finalElapsedMs) => {
        setRunning(false)
        if (finalElapsedMs > 0) {
          setElapsedMs(finalElapsedMs)
        }
      },
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

  return { update, running, error, elapsedMs, logs }
}
