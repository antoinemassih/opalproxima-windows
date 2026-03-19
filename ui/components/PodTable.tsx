interface Pod {
  name: string
  status: string
  ready: boolean
}

export function PodTable({ namespace, pods }: { namespace: string; pods: Pod[] }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{
        fontSize: 16, fontWeight: 700, marginBottom: 12,
        textTransform: 'uppercase', color: 'var(--text-muted)',
        margin: '0 0 12px 0',
      }}>
        {namespace}
      </h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Pod</th>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Phase</th>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Ready</th>
          </tr>
        </thead>
        <tbody>
          {pods.map((p) => (
            <tr key={p.name} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '8px 0' }}>{p.name}</td>
              <td style={{ padding: '8px 0' }}>{p.status}</td>
              <td style={{ padding: '8px 0', color: p.ready ? 'var(--running)' : 'var(--error)' }}>
                {p.ready ? '✓' : '✗'}
              </td>
            </tr>
          ))}
          {pods.length === 0 && (
            <tr>
              <td colSpan={3} style={{ padding: '8px 0', color: 'var(--text-muted)' }}>No pods</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
