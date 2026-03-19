import type { Metadata } from 'next'
import '@/styles/themes.css'
import './globals.css'

export const metadata: Metadata = {
  title: 'DevHub',
  description: 'OpalProxima Windows — local dev hub',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh', margin: 0 }}>
        <nav style={{
          background: 'var(--bg-card)',
          borderBottom: '1px solid var(--border)',
          padding: '12px 32px',
          display: 'flex',
          gap: 24,
          fontSize: 14,
        }}>
          <a href="/" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>DevHub</a>
          <a href="/projects" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Projects</a>
          <a href="/infrastructure" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Infrastructure</a>
        </nav>
        {children}
      </body>
    </html>
  )
}
