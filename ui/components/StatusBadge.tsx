const colors: Record<string, string> = {
  running: 'var(--running)',
  stopped: 'var(--stopped)',
  error: 'var(--error)',
  deploying: 'var(--deploying)',
  unknown: 'var(--unknown)',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{
      background: colors[status] || 'var(--stopped)',
      color: '#fff',
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'uppercase',
    }}>
      {status}
    </span>
  )
}
