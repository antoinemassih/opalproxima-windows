import { LogViewer } from '@/components/LogViewer'

export default async function LogsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Logs</h1>
      <LogViewer projectId={id} />
    </main>
  )
}
