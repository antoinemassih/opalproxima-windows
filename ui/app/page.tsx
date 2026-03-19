import { getStatus, getK8s } from '@/lib/api'

export const dynamic = 'force-dynamic'

interface StatusResult {
  ok: boolean
  projects_running: number
  k8s_available: boolean
  warnings: string[]
}

interface Pod {
  name: string
  ready: boolean
  status: string
}

interface K8sResult {
  dev: Pod[]
  prod: Pod[]
  available: boolean
}

export default async function DashboardPage() {
  let status: StatusResult = { ok: false, projects_running: 0, k8s_available: false, warnings: [] }
  let k8s: K8sResult = { dev: [], prod: [], available: false }

  try {
    [status, k8s] = await Promise.all([getStatus(), getK8s()])
  } catch {
    // Daemon not running — show disconnected state
  }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Dashboard</h1>

      {!status.ok && (
        <div style={{ background: 'var(--error)', color: '#fff', borderRadius: 6, padding: 12, marginBottom: 24 }}>
          Daemon not connected — start DevHub.exe to connect
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        <SummaryCard label="Projects Running" value={status.projects_running} color="var(--running)" />
        <SummaryCard
          label="K8s"
          value={status.k8s_available ? 'Connected' : 'Unavailable'}
          color={status.k8s_available ? 'var(--running)' : 'var(--error)'}
        />
        <SummaryCard
          label="Warnings"
          value={status.warnings?.length ?? 0}
          color={(status.warnings?.length ?? 0) > 0 ? 'var(--warning)' : 'var(--running)'}
        />
      </div>

      {status.warnings?.length > 0 && (
        <div style={{ background: 'var(--warning)', color: '#000', borderRadius: 6, padding: 12, marginBottom: 24 }}>
          {status.warnings.map((w: string, i: number) => <div key={i}>{w}</div>)}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <PodSummary namespace="dev" pods={k8s.dev ?? []} />
        <PodSummary namespace="prod" pods={k8s.prod ?? []} />
      </div>
    </main>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{String(value)}</div>
    </div>
  )
}

function PodSummary({ namespace, pods }: { namespace: string; pods: Pod[] }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-muted)', textTransform: 'uppercase', margin: '0 0 12px 0' }}>
        {namespace}
      </h2>
      {pods.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No pods</div>
        : pods.map((p: Pod) => (
            <div key={p.name} style={{
              display: 'flex', justifyContent: 'space-between', padding: '4px 0',
              borderBottom: '1px solid var(--border)', fontSize: 13
            }}>
              <span>{p.name}</span>
              <span style={{ color: p.ready ? 'var(--running)' : 'var(--error)' }}>
                {p.ready ? 'Ready' : p.status}
              </span>
            </div>
          ))
      }
    </div>
  )
}
