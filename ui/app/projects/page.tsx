import { getProjects } from '@/lib/api'
import { ProjectCard } from '@/components/ProjectCard'

export const dynamic = 'force-dynamic'

interface Project {
  id: string
  name: string
  path: string
  type: string
  status: string
  port?: number
  k3s_app_name?: string
}

export default async function ProjectsPage() {
  let projects: Project[] = []
  try {
    projects = await getProjects()
  } catch {
    // Daemon not running
  }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Projects</h1>
      {projects.length === 0
        ? <div style={{ color: 'var(--text-muted)' }}>No projects yet. Add one via the tray menu.</div>
        : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
            {projects.map((p: Project) => <ProjectCard key={p.id} project={p} />)}
          </div>
      }
    </main>
  )
}
