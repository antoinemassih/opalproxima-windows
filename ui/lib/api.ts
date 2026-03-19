const DAEMON_URL = process.env.DAEMON_URL || 'http://localhost:7477'
const DAEMON_TOKEN = process.env.DAEMON_TOKEN || ''

export async function daemonFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${DAEMON_URL}${path}`, {
    ...init,
    headers: {
      'Authorization': `Bearer ${DAEMON_TOKEN}`,
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`Daemon error ${res.status}: ${path}`)
  return res.json()
}

export const getProjects = () => daemonFetch('/projects')
export const getStatus = () => daemonFetch('/status')
export const getK8s = () => daemonFetch('/k8s')
export const getCi = () => daemonFetch('/ci')
export const startProject = (id: string) => daemonFetch(`/projects/${id}/start`, { method: 'POST' })
export const stopProject = (id: string) => daemonFetch(`/projects/${id}/stop`, { method: 'POST' })
export const deployProject = (id: string) => daemonFetch(`/projects/${id}/deploy`, { method: 'POST' })
export const promoteProject = (id: string) => daemonFetch(`/projects/${id}/promote`, { method: 'POST' })
