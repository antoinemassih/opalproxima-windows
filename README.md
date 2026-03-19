# OpalProxima Windows

Windows dev hub — system tray, daemon, and dashboard for managing local development infrastructure.

## Stack

- **Tray**: C# WinForms system tray app
- **Daemon**: Python FastAPI on `127.0.0.1:7477`
- **Dashboard**: Next.js 14
- **Routing**: Caddy at `devhub.localhost`

## Structure

```
devhub-repo/
├── daemon/          # Python FastAPI daemon
│   ├── routers/     # API route modules
│   └── tests/       # Daemon tests
├── ui/              # Next.js 14 dashboard
├── tray/            # C# WinForms tray app
│   └── DevHub/
├── docs/            # Specs and plans
└── Caddyfile        # Local reverse proxy config
```

## Getting Started

See `docs/` for specs and implementation plans.
