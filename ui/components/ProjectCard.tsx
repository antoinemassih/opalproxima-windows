import { StatusBadge } from './StatusBadge'

interface Project {
  id: string
  name: string
  path: string
  type: string
  status: string
  port?: number
  k3s_app_name?: string
}

async function projectAction(id: string, action: string) {
  'use server'
  const { daemonFetch } = await import('@/lib/api')
  await daemonFetch(`/projects/${id}/${action}`, { method: 'POST' })
}

export function ProjectCard({ project }: { project: Project }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>{project.name}</span>
        <StatusBadge status={project.status} />
      </div>
      <div style={{ color: 'var(--text-muted)', fontSize: 12, wordBreak: 'break-all' }}>{project.path}</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
        <form action={projectAction.bind(null, project.id, 'start')}>
          <button type="submit" style={btnStyle('var(--running)')}>Start</button>
        </form>
        <form action={projectAction.bind(null, project.id, 'stop')}>
          <button type="submit" style={btnStyle('var(--error)')}>Stop</button>
        </form>
        {project.k3s_app_name && (
          <form action={projectAction.bind(null, project.id, 'deploy')}>
            <button type="submit" style={btnStyle('var(--accent)')}>Deploy</button>
          </form>
        )}
        {project.port && (
          <a href={`http://localhost:${project.port}`} target="_blank" rel="noreferrer"
             style={{ ...btnStyle('var(--text-muted)'), textDecoration: 'none', display: 'inline-block' }}>
            Open
          </a>
        )}
      </div>
    </div>
  )
}

const btnStyle = (bg: string): React.CSSProperties => ({
  background: bg,
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  padding: '4px 10px',
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
})
