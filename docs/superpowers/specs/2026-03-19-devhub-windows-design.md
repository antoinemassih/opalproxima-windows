# DevHub Windows Design Spec
_2026-03-19_

## Overview

A standalone Windows dev hub — the Windows equivalent of OpalProxima on Mac. Manages local development projects on the Windows machine, integrates with the homelab K3s cluster, and lets the user see at a glance what is running, deployed, and healthy.

**Repo:** `antoinemassih/opalproxima-windows`

---

## Stack

| Layer | Technology |
|-------|-----------|
| System tray | C# WinForms (.NET 8, self-contained exe) |
| Local daemon | Python 3.11, FastAPI, SQLite |
| Dashboard UI | Next.js 14, coralbeef theme system |
| Local routing | Caddy (`devhub.localhost`) |
| Infra integrations | kubectl (WSL or native), Gitea API, psutil |

---

## Folder Layout

```
C:\Users\USER\devhub\
├── tray\                   # C# WinForms project (DevHub.sln)
├── daemon\
│   ├── main.py
│   ├── routers\
│   │   ├── projects.py
│   │   ├── k8s.py
│   │   └── ci.py
│   ├── devhub.db
│   ├── config.json
│   └── requirements.txt
├── ui\
│   └── .next\              # Pre-built output (must exist at runtime)
├── caddy\                  # Per-project optional config files
├── caddy.exe               # Caddy binary (bundled)
└── Caddyfile
```

**Release zip structure:**
```
opalproxima-windows-vX.X.X.zip
├── DevHub.exe
├── caddy.exe
├── Caddyfile
├── daemon\       (full daemon directory)
└── ui\.next\     (pre-built Next.js output)
```

---

## Component: C# WinForms Tray App

**Startup sequence:**
1. Launch `daemon\main.py` via Python as a background process (bound to 127.0.0.1:7477)
2. Launch `caddy.exe run --config Caddyfile` as a background process
3. Launch `npm run start` inside `ui\` on the configured `ui_port` (default 3000) as a background process
4. Poll `http://localhost:7477/status` with exponential backoff (250ms → 500ms → 1s → 2s, max 10 retries) before marking daemon ready
5. Once ready, switch to 5s polling with bearer token from `config.json`

All three child processes are tracked by handle. On crash, the tray restarts the process and fires a toast notification. On quit, all are terminated cleanly via their Windows process handles.

**Tray icon states:** idle (grey), active (blue), warning (yellow — crash or CI failure)

**Tray menu:**
- _Project list_ — each project shows name + status badge
  - Submenu per project: Start, Stop, Open in browser, Deploy to dev, Promote to prod
- Open Dashboard → opens `http://devhub.localhost` in default browser
- Separator
- Start All / Stop All
- Separator
- Quit (graceful shutdown of all managed processes)

**Windows integration:**
- Startup registry key: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Toast notifications via `Microsoft.Toolkit.Uwp.Notifications`

**Packaging:** `dotnet publish -r win-x64 --self-contained` → single `.exe`. CI also runs `next build` and zips everything together (see release zip structure above).

---

## Component: Python Daemon

FastAPI on `127.0.0.1:7477` only — never `0.0.0.0`.

**Authentication:** All requests require `Authorization: Bearer <token>`. Token is generated on first run via `secrets.token_hex(32)`, stored in `config.json`. The Next.js server-side code reads the token from its environment and attaches it on API calls — Caddy does not inject it.

**Startup validation:** On startup, the daemon validates `kubectl_cmd` and `k3s_app_cmd` by running a test command (e.g. `kubectl version --client`). If validation fails, daemon still starts but marks K8s integration as `unavailable` and returns a warning in `/status`. The tray shows a yellow icon and a toast.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Daemon health, summary counts, integration availability |
| GET | `/projects` | All projects with current status |
| POST | `/projects` | Add project (auto-detect type) |
| DELETE | `/projects/{id}` | Remove project |
| POST | `/projects/{id}/start` | Start dev process |
| POST | `/projects/{id}/stop` | Stop dev process |
| GET | `/projects/{id}/logs` | SSE log stream |
| POST | `/projects/{id}/deploy` | `k3s-app deploy` via subprocess |
| POST | `/projects/{id}/promote` | `k3s-app promote` via subprocess |
| GET | `/k8s` | Pod health (dev + prod namespaces) |
| GET | `/ci` | Gitea CI status for tracked repos |
| GET | `/events` | SSE stream for tray notifications |

**Project type auto-detection:**

| File present | Detected type | Default start cmd |
|-------------|--------------|------------------|
| `package.json` | `nextjs` / `node` | `npm run dev` |
| `pyproject.toml` / `requirements.txt` | `python` | `uvicorn main:app --reload` |
| `k3s.yaml` present | sets `k3s_app_name` | — |

**Process management on Windows:**
- Child processes launched via `subprocess.Popen` with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`
- Stopped via `os.kill(pid, signal.CTRL_BREAK_EVENT)` which terminates the full process tree
- On daemon startup: any project with a non-NULL `process_pid` is checked via `psutil.pid_exists()`. If the PID is gone → status set to `unknown`. If PID exists but belongs to a different process → status set to `unknown`. Dashboard shows a warning badge for `unknown` projects; user can dismiss to mark as `stopped`.
- `process_pid` is set to `NULL` when a process stops normally or is confirmed dead

**Log handling:**
- Logs are streamed via SSE and held in a per-project in-memory ring buffer (last 500 lines) for the lifetime of the daemon session
- Ring buffer is cleared when a project process stops or restarts
- Logs are not persisted to disk — this is a known v1 limitation

**Background workers:**
- Every 5s: process health via psutil, crash detection → `/events` SSE
- Every 60s: K8s pod status refresh, Gitea CI refresh
- K8s and CI data held in memory only (not written to SQLite)

---

## Component: Next.js Dashboard

Next.js 14, coralbeef 6-theme system, Zustand. **Must be pre-built** (`next build`) before deployment — `ui\.next\` must exist at runtime or `next start` will fail. The CI step runs `next build` and includes the output in the release zip.

`next start` is launched by the tray app on `ui_port` (from `config.json`, default 3000). Port 3000 is commonly used; if taken, the user configures an alternate port in `config.json` and restarts. The tray does not auto-detect port conflicts in v1 — if `next start` fails to bind, it is treated as a crash and a toast is shown.

**Pages:**
- **Dashboard** — summary: projects running/stopped/error, K8s pod health (dev/prod), CI status, integration warnings
- **Projects** — list with status badges, git info (branch/dirty/ahead-behind), start/stop/deploy/promote buttons
- **Logs** — per-project SSE log viewer (ring buffer, clears on process restart)
- **Infrastructure** — K8s pod table across dev + prod with health indicators

**Token:** Next.js server-side code (API routes / server components) reads `DAEMON_TOKEN` from its environment and attaches `Authorization: Bearer <token>` on all calls to `localhost:7477`. The token is never sent to the browser.

---

## Component: Caddy

Bundled at `devhub\caddy.exe`. Tray launches it directly.

**Caddyfile:**
```
devhub.localhost {
    reverse_proxy /api/* localhost:7477
    reverse_proxy /* localhost:3000
}
```

Note: Caddy does not inject the bearer token. Token attachment is handled server-side in Next.js. Caddy is purely a reverse proxy for local URL routing.

Per-project entries can be added in `caddy\{name}.conf` and included via Caddy's `import` directive for locally running app ports.

---

## Config (`daemon\config.json`)

```json
{
  "daemon_token": "<generated on first run via secrets.token_hex(32)>",
  "gitea_url": "http://192.168.1.42:3000",
  "gitea_token": "...",
  "kubeconfig": "C:/Users/USER/.kube/config",
  "registry": "192.168.1.71:5000",
  "kubectl_cmd": "wsl kubectl",
  "k3s_app_cmd": "wsl k3s-app",
  "ui_port": 3000
}
```

---

## Data Model (SQLite)

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    type TEXT,           -- 'nextjs', 'node', 'python'
    port INTEGER,
    start_cmd TEXT,
    gitea_repo TEXT,
    github_repo TEXT,
    k3s_app_name TEXT,
    process_pid INTEGER, -- NULL when stopped or dead
    status TEXT DEFAULT 'stopped',
    -- status values: 'stopped', 'running', 'error', 'deploying', 'unknown'
    created_at TEXT,
    updated_at TEXT
);

-- Logs: in-memory ring buffer only (last 500 lines per project, not persisted)
-- K8s + CI data: in-memory only, refreshed every 60s
```

---

## Repository & CI

- **GitHub:** `antoinemassih/opalproxima-windows`
- **Gitea mirror:** `gitea-mirror antoinemassih/opalproxima-windows`
- **CI (Gitea Actions):**
  - On push to `main`: `dotnet publish` + `next build` + zip → dev artifact
  - On version tag: publish GitHub release with zip artifact

---

## Out of Scope (v1)

- LunarBadger worktree integration
- Multi-user support
- Remote access
- Installer packaging (zip is sufficient)
- Automatic port conflict resolution
- Persistent log storage
