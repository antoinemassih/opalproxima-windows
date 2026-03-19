import { getK8s } from '@/lib/api'
import { PodTable } from '@/components/PodTable'

export const dynamic = 'force-dynamic'

interface K8sResult {
  dev: Pod[]
  prod: Pod[]
  available: boolean
  error?: string
}

interface Pod {
  name: string
  status: string
  ready: boolean
}

export default async function InfrastructurePage() {
  let k8s: K8sResult = { dev: [], prod: [], available: false }
  try {
    k8s = await getK8s()
  } catch {
    // Daemon not running
  }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Infrastructure</h1>
      {!k8s.available && (
        <div style={{
          background: 'var(--error)', color: '#fff',
          borderRadius: 6, padding: 12, marginBottom: 24,
        }}>
          {k8s.error ? `K8s unavailable: ${k8s.error}` : 'K8s not connected'}
        </div>
      )}
      <PodTable namespace="dev" pods={k8s.dev ?? []} />
      <PodTable namespace="prod" pods={k8s.prod ?? []} />
    </main>
  )
}
