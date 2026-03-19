'use client'
import { useEffect, useRef, useState } from 'react'

export function LogViewer({ projectId }: { projectId: string }) {
  const [lines, setLines] = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const es = new EventSource(`/api/projects/${projectId}/logs`)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data) as { line: string }
      setLines(prev => [...prev.slice(-499), data.line])
    }
    return () => es.close()
  }, [projectId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: 16,
      fontFamily: 'monospace',
      fontSize: 13,
      height: '70vh',
      overflowY: 'auto',
    }}>
      {lines.length === 0
        ? <span style={{ color: 'var(--text-muted)' }}>No logs yet...</span>
        : lines.map((l, i) => (
            <div key={i} style={{ lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{l}</div>
          ))
      }
      <div ref={bottomRef} />
    </div>
  )
}
