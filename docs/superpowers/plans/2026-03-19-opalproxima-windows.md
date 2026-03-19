# OpalProxima Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Windows dev hub (OpalProxima Windows) — system tray app + Python daemon + Next.js dashboard — that manages local dev projects and integrates with the homelab K3s cluster.

**Architecture:** C# WinForms tray app manages three background processes (Python FastAPI daemon on 127.0.0.1:7477, Next.js dashboard on port 3000, Caddy reverse proxy). The daemon owns all business logic and state (SQLite). The dashboard is a read/write UI over the daemon API. The tray app provides Windows-native notifications and quick actions.

**Tech Stack:** Python 3.11 + FastAPI + aiosqlite + psutil, Next.js 14 + Zustand + coralbeef themes, C# .NET 8 WinForms, Caddy, SQLite

---

## File Map

### Phase 1 — Repo & Structure
```
devhub/
├── .github/workflows/build.yml
├── .gitea/workflows/build.yml
├── .gitignore
├── README.md
├── Caddyfile
└── docs/superpowers/specs/ + plans/  (already exists)
```

### Phase 2 — Python Daemon
```
daemon/
├── main.py               # FastAPI app, startup, lifespan
├── config.py             # config.json loading + token generation
├── database.py           # aiosqlite setup, migrations
├── auth.py               # bearer token dependency
├── models.py             # Pydantic + SQLite row models
├── process_manager.py    # Windows process lifecycle (Popen, CTRL_BREAK)
├── log_buffer.py         # Per-project in-memory ring buffer (500 lines)
├── background.py         # 5s health + 60s K8s/CI refresh tasks
├── routers/
│   ├── projects.py       # CRUD + start/stop/logs/deploy/promote
│   ├── k8s.py            # kubectl pod health
│   └── ci.py             # Gitea CI status
├── requirements.txt
└── tests/
    ├── conftest.py
    ├── test_projects.py
    ├── test_process_manager.py
    └── test_log_buffer.py
```

### Phase 3 — Next.js Dashboard
```
ui/
├── package.json
├── next.config.js        # API rewrites → localhost:7477
├── .env.local            # DAEMON_TOKEN, DAEMON_URL
├── app/
│   ├── layout.tsx        # Root layout, theme provider
│   ├── page.tsx          # Dashboard (summary cards)
│   ├── projects/
│   │   └── page.tsx      # Projects list
│   ├── logs/
│   │   └── [id]/page.tsx # SSE log viewer
│   └── infrastructure/
│       └── page.tsx      # K8s pod table
├── lib/
│   ├── api.ts            # Server-side API client (attaches token)
│   └── store.ts          # Zustand store
├── components/
│   ├── StatusBadge.tsx
│   ├── ProjectCard.tsx
│   ├── LogViewer.tsx
│   └── PodTable.tsx
└── styles/
    └── themes.css        # Coralbeef 6-theme variables
```

### Phase 4 — C# Tray App
```
tray/
├── DevHub.sln
└── DevHub/
    ├── DevHub.csproj
    ├── Program.cs            # Entry point, single-instance check
    ├── TrayApp.cs            # NotifyIcon, menu, polling loop
    ├── ProcessManager.cs     # Manages daemon/caddy/ui processes
    ├── DaemonClient.cs       # HTTP client → localhost:7477
    ├── StartupHelper.cs      # Registry startup key
    ├── ToastHelper.cs        # Windows toast notifications
    └── Models/
        ├── ProjectStatus.cs
        └── DaemonStatus.cs
```

---

## Phase 1: Repo & Project Structure

### Task 1: Create GitHub repo and initialize project

**Files:**
- Create: `devhub/.gitignore`
- Create: `devhub/README.md`
- Create: `devhub/Caddyfile`

- [ ] **Step 1: Create GitHub repo**

```bash
cd /c/Users/USER/documents/development
gh repo create antoinemassih/opalproxima-windows --public --description "Windows dev hub — OpalProxima for Windows"
git clone https://github.com/antoinemassih/opalproxima-windows devhub-repo
cp -r devhub/docs devhub-repo/
cd devhub-repo
```

- [ ] **Step 2: Create .gitignore**

```
# Python
__pycache__/
*.pyc
.venv/
daemon/devhub.db
daemon/config.json

# Node
ui/node_modules/
ui/.next/
ui/.env.local

# C#
tray/*/bin/
tray/*/obj/
*.user

# Misc
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create Caddyfile**

```
devhub.localhost {
    reverse_proxy /api/* localhost:7477
    reverse_proxy /* localhost:3000
}
```

- [ ] **Step 4: Create folder structure**

```bash
mkdir -p daemon/routers daemon/tests ui/app ui/lib ui/components ui/styles tray/DevHub
```

- [ ] **Step 5: Initial commit**

```bash
git add .
git commit -m "chore: initialize opalproxima-windows repo structure"
git push origin main
```

- [ ] **Step 6: Mirror to Gitea**

```bash
gitea-mirror antoinemassih/opalproxima-windows
```

---

## Phase 2: Python Daemon

### Task 2: Config and database foundation

**Files:**
- Create: `daemon/config.py`
- Create: `daemon/database.py`
- Create: `daemon/models.py`
- Create: `daemon/requirements.txt`
- Create: `daemon/tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
aiosqlite==0.20.0
pydantic==2.7.0
httpx==0.27.0
psutil==5.9.8
pyyaml==6.0.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 2: Write test for config loading**

`daemon/tests/test_config.py`:
```python
import json, os, tempfile, pytest
from pathlib import Path

def test_config_generates_token_on_first_run(tmp_path):
    config_path = tmp_path / "config.json"
    from daemon.config import load_config
    cfg = load_config(config_path)
    assert len(cfg["daemon_token"]) == 64  # 32 bytes hex
    assert config_path.exists()

def test_config_reuses_existing_token(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"daemon_token": "abc123"}))
    from daemon.config import load_config
    cfg = load_config(config_path)
    assert cfg["daemon_token"] == "abc123"
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd daemon && python -m pytest tests/test_config.py -v
```
Expected: `ImportError: No module named 'daemon.config'`

- [ ] **Step 4: Implement config.py**

`daemon/config.py`:
```python
import json, secrets
from pathlib import Path

DEFAULTS = {
    "daemon_token": "",
    "gitea_url": "http://192.168.1.42:3000",
    "gitea_token": "",
    "kubeconfig": "C:/Users/USER/.kube/config",
    "registry": "192.168.1.71:5000",
    "kubectl_cmd": "wsl kubectl",
    "k3s_app_cmd": "wsl k3s-app",
    "ui_port": 3000,
}

def load_config(path: Path = Path("config.json")) -> dict:
    cfg = {**DEFAULTS}
    if path.exists():
        cfg.update(json.loads(path.read_text()))
    if not cfg["daemon_token"]:
        cfg["daemon_token"] = secrets.token_hex(32)
        path.write_text(json.dumps(cfg, indent=2))
    return cfg

CONFIG = load_config()
```

- [ ] **Step 5: Run test — expect PASS**

```bash
python -m pytest tests/test_config.py -v
```

- [ ] **Step 6: Write database test**

`daemon/tests/test_database.py`:
```python
import pytest, asyncio
import aiosqlite

@pytest.mark.asyncio
async def test_projects_table_created(tmp_path):
    db_path = tmp_path / "test.db"
    from daemon.database import init_db
    async with aiosqlite.connect(db_path) as db:
        await init_db(db)
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cur:
            tables = [r[0] async for r in cur]
    assert "projects" in tables
```

- [ ] **Step 7: Implement database.py**

`daemon/database.py`:
```python
import aiosqlite
from pathlib import Path

DB_PATH = Path("devhub.db")

CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    type TEXT,
    port INTEGER,
    start_cmd TEXT,
    gitea_repo TEXT,
    github_repo TEXT,
    k3s_app_name TEXT,
    process_pid INTEGER,
    status TEXT DEFAULT 'stopped',
    created_at TEXT,
    updated_at TEXT
)
"""

async def init_db(db: aiosqlite.Connection):
    await db.execute(CREATE_PROJECTS)
    await db.commit()

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
```

- [ ] **Step 8: Run all daemon tests so far**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 9: Commit**

```bash
git add daemon/
git commit -m "feat(daemon): config loading, token generation, SQLite init"
```

---

### Task 3: Auth and models

**Files:**
- Create: `daemon/auth.py`
- Create: `daemon/models.py`

- [ ] **Step 1: Write auth test**

`daemon/tests/test_auth.py`:
```python
import pytest
import daemon.config as cfg_module
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from daemon.auth import require_token

app = FastAPI()

@app.get("/protected")
async def protected(token=Depends(require_token)):
    return {"ok": True}

client = TestClient(app)

def test_no_token_returns_401():
    r = client.get("/protected")
    assert r.status_code == 401

def test_wrong_token_returns_403(monkeypatch):
    # Patch CONFIG in place so auth.py sees the updated token
    monkeypatch.setitem(cfg_module.CONFIG, "daemon_token", "realtoken")
    r = client.get("/protected", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403

def test_correct_token_passes(monkeypatch):
    monkeypatch.setitem(cfg_module.CONFIG, "daemon_token", "testtoken")
    r = client.get("/protected", headers={"Authorization": "Bearer testtoken"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
python -m pytest tests/test_auth.py -v
```

- [ ] **Step 3: Implement auth.py**

`daemon/auth.py`:
```python
from fastapi import Header, HTTPException, Depends
from daemon.config import CONFIG

async def require_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization[7:]
    if token != CONFIG["daemon_token"]:
        raise HTTPException(403, "Invalid token")
    return token
```

- [ ] **Step 4: Implement models.py**

`daemon/models.py`:
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class ProjectCreate(BaseModel):
    name: str
    path: str
    type: Optional[str] = None
    port: Optional[int] = None
    start_cmd: Optional[str] = None
    gitea_repo: Optional[str] = None
    github_repo: Optional[str] = None
    k3s_app_name: Optional[str] = None

class Project(ProjectCreate):
    id: str
    process_pid: Optional[int] = None
    status: str = "stopped"  # stopped, running, error, deploying, unknown
    created_at: str
    updated_at: str

class DaemonStatus(BaseModel):
    ok: bool
    projects_running: int
    k8s_available: bool
    gitea_available: bool
    warnings: list[str] = []
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add daemon/auth.py daemon/models.py daemon/tests/test_auth.py
git commit -m "feat(daemon): bearer token auth, Pydantic models"
```

---

### Task 4: Process manager

**Files:**
- Create: `daemon/process_manager.py`
- Create: `daemon/log_buffer.py`
- Test: `daemon/tests/test_process_manager.py`
- Test: `daemon/tests/test_log_buffer.py`

- [ ] **Step 1: Write log buffer test**

`daemon/tests/test_log_buffer.py`:
```python
from daemon.log_buffer import LogBuffer

def test_buffer_stores_lines():
    buf = LogBuffer(max_lines=5)
    buf.append("line1")
    buf.append("line2")
    assert buf.lines() == ["line1", "line2"]

def test_buffer_evicts_oldest_at_max():
    buf = LogBuffer(max_lines=3)
    for i in range(5):
        buf.append(f"line{i}")
    lines = buf.lines()
    assert len(lines) == 3
    assert lines[0] == "line2"

def test_buffer_clear():
    buf = LogBuffer()
    buf.append("x")
    buf.clear()
    assert buf.lines() == []
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_log_buffer.py -v
```

- [ ] **Step 3: Implement log_buffer.py**

`daemon/log_buffer.py`:
```python
from collections import deque
from threading import Lock

class LogBuffer:
    def __init__(self, max_lines: int = 500):
        self._buf = deque(maxlen=max_lines)
        self._lock = Lock()

    def append(self, line: str):
        with self._lock:
            self._buf.append(line)

    def lines(self) -> list[str]:
        with self._lock:
            return list(self._buf)

    def clear(self):
        with self._lock:
            self._buf.clear()

# Global registry: project_id → LogBuffer
_buffers: dict[str, LogBuffer] = {}

def get_buffer(project_id: str) -> LogBuffer:
    if project_id not in _buffers:
        _buffers[project_id] = LogBuffer()
    return _buffers[project_id]

def clear_buffer(project_id: str):
    if project_id in _buffers:
        _buffers[project_id].clear()
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_log_buffer.py -v
```

- [ ] **Step 5: Write process manager test**

`daemon/tests/test_process_manager.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from daemon.process_manager import ProcessManager

def test_start_records_pid():
    pm = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    with patch("subprocess.Popen", return_value=mock_proc):
        pid = pm.start("proj1", "echo hello", "C:/tmp")
    assert pid == 1234
    assert pm.is_running("proj1")

def test_stop_sends_ctrl_break():
    pm = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.pid = 5678
    with patch("subprocess.Popen", return_value=mock_proc):
        pm.start("proj1", "echo hello", "C:/tmp")
    pm.stop("proj1")
    mock_proc.send_signal.assert_called_once()

def test_is_running_false_when_not_started():
    pm = ProcessManager()
    assert not pm.is_running("nonexistent")
```

- [ ] **Step 6: Implement process_manager.py**

`daemon/process_manager.py`:
```python
import subprocess, signal, os
import psutil
from daemon.log_buffer import get_buffer, clear_buffer

class ProcessManager:
    def __init__(self):
        self._procs: dict[str, subprocess.Popen] = {}

    def start(self, project_id: str, cmd: str, cwd: str) -> int:
        clear_buffer(project_id)
        buf = get_buffer(project_id)
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            text=True,
            bufsize=1,
        )
        self._procs[project_id] = proc
        # Stream output to log buffer in background thread
        import threading
        def _reader():
            for line in proc.stdout:
                buf.append(line.rstrip())
        threading.Thread(target=_reader, daemon=True).start()
        return proc.pid

    def stop(self, project_id: str):
        proc = self._procs.pop(project_id, None)
        if proc:
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def is_running(self, project_id: str) -> bool:
        proc = self._procs.get(project_id)
        if not proc:
            return False
        return proc.poll() is None

    def validate_stale_pids(self, projects: list[dict]) -> list[str]:
        """Returns IDs of projects whose stored PID is stale."""
        stale = []
        for p in projects:
            pid = p.get("process_pid")
            if pid and not psutil.pid_exists(pid):
                stale.append(p["id"])
        return stale

# Global instance
process_manager = ProcessManager()
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add daemon/process_manager.py daemon/log_buffer.py daemon/tests/
git commit -m "feat(daemon): process manager (Windows job groups), log ring buffer"
```

---

### Task 5: Projects router

**Files:**
- Create: `daemon/routers/projects.py`
- Test: `daemon/tests/test_projects.py`

- [ ] **Step 1: Write project CRUD tests**

`daemon/tests/test_projects.py`:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json

TOKEN = "testtoken"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

@pytest.fixture
def client():
    import os; os.environ["DAEMON_TOKEN"] = TOKEN
    from daemon.main import app
    with TestClient(app) as c:
        yield c

def test_list_projects_empty(client):
    r = client.get("/projects", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []

def test_add_project(client, tmp_path):
    r = client.post("/projects", headers=HEADERS, json={
        "name": "myapp",
        "path": str(tmp_path),
    })
    assert r.status_code == 200
    assert r.json()["name"] == "myapp"
    assert r.json()["status"] == "stopped"

def test_add_project_requires_auth(client, tmp_path):
    r = client.post("/projects", json={"name": "x", "path": str(tmp_path)})
    assert r.status_code == 401

def test_delete_project(client, tmp_path):
    r = client.post("/projects", headers=HEADERS, json={"name": "del", "path": str(tmp_path)})
    pid = r.json()["id"]
    r2 = client.delete(f"/projects/{pid}", headers=HEADERS)
    assert r2.status_code == 200
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_projects.py -v
```

- [ ] **Step 3: Implement routers/projects.py**

`daemon/routers/projects.py`:
```python
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio, json

from daemon.auth import require_token
from daemon.database import get_db
from daemon.models import ProjectCreate, Project
from daemon.process_manager import process_manager
from daemon.log_buffer import get_buffer

router = APIRouter(prefix="/projects", tags=["projects"])

def _detect_type(path: str) -> tuple[str, str]:
    p = Path(path)
    if (p / "package.json").exists():
        return "nextjs", "npm run dev"
    if (p / "pyproject.toml").exists() or (p / "requirements.txt").exists():
        return "python", "uvicorn main:app --reload"
    return "unknown", ""

def _check_k3s(path: str) -> str | None:
    p = Path(path) / "k3s.yaml"
    if p.exists():
        import yaml
        data = yaml.safe_load(p.read_text())
        return data.get("app")
    return None

@router.get("")
async def list_projects(db=Depends(get_db), _=Depends(require_token)):
    async with db.execute("SELECT * FROM projects") as cur:
        rows = [dict(r) async for r in cur]
    return rows

@router.post("")
async def add_project(body: ProjectCreate, db=Depends(get_db), _=Depends(require_token)):
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    typ, cmd = _detect_type(body.path)
    k3s_app = _check_k3s(body.path)
    await db.execute(
        """INSERT INTO projects (id,name,path,type,port,start_cmd,gitea_repo,github_repo,
           k3s_app_name,process_pid,status,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,NULL,'stopped',?,?)""",
        (pid, body.name, body.path, body.type or typ, body.port,
         body.start_cmd or cmd, body.gitea_repo, body.github_repo,
         body.k3s_app_name or k3s_app, now, now)
    )
    await db.commit()
    async with db.execute("SELECT * FROM projects WHERE id=?", (pid,)) as cur:
        row = dict(await cur.fetchone())
    return row

@router.delete("/{project_id}")
async def delete_project(project_id: str, db=Depends(get_db), _=Depends(require_token)):
    process_manager.stop(project_id)
    await db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    await db.commit()
    return {"ok": True}

@router.post("/{project_id}/start")
async def start_project(project_id: str, db=Depends(get_db), _=Depends(require_token)):
    async with db.execute("SELECT * FROM projects WHERE id=?", (project_id,)) as cur:
        row = dict(await cur.fetchone())
    pid = process_manager.start(project_id, row["start_cmd"], row["path"])
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE projects SET status='running', process_pid=?, updated_at=? WHERE id=?",
        (pid, now, project_id)
    )
    await db.commit()
    return {"ok": True, "pid": pid}

@router.post("/{project_id}/stop")
async def stop_project(project_id: str, db=Depends(get_db), _=Depends(require_token)):
    process_manager.stop(project_id)
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE projects SET status='stopped', process_pid=NULL, updated_at=? WHERE id=?",
        (now, project_id)
    )
    await db.commit()
    return {"ok": True}

@router.get("/{project_id}/logs")
async def stream_logs(project_id: str, _=Depends(require_token)):
    buf = get_buffer(project_id)
    async def generate():
        for line in buf.lines():
            yield f"data: {json.dumps({'line': line})}\n\n"
        # Stream new lines as they arrive
        seen = len(buf.lines())
        while True:
            lines = buf.lines()
            for line in lines[seen:]:
                yield f"data: {json.dumps({'line': line})}\n\n"
            seen = len(lines)
            await asyncio.sleep(0.2)
    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 4: Create main.py skeleton**

`daemon/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiosqlite
from daemon.database import init_db, DB_PATH
from daemon.routers import projects, k8s, ci
from daemon.config import CONFIG

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await init_db(db)
    yield

app = FastAPI(title="DevHub Daemon", lifespan=lifespan)
app.include_router(projects.router)
app.include_router(k8s.router)
app.include_router(ci.router)

@app.get("/status")
async def status():
    return {"ok": True, "projects_running": 0, "k8s_available": True, "gitea_available": True, "warnings": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=7477, reload=False)
```

- [ ] **Step 5: Create stub routers for k8s and ci**

`daemon/routers/k8s.py`:
```python
from fastapi import APIRouter, Depends
from daemon.auth import require_token
router = APIRouter(prefix="/k8s", tags=["k8s"])

@router.get("")
async def pod_health(_=Depends(require_token)):
    return {"dev": [], "prod": []}
```

`daemon/routers/ci.py`:
```python
from fastapi import APIRouter, Depends
from daemon.auth import require_token
router = APIRouter(prefix="/ci", tags=["ci"])

@router.get("")
async def ci_status(_=Depends(require_token)):
    return []
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 7: Commit**

```bash
git add daemon/
git commit -m "feat(daemon): projects router — CRUD, start/stop, SSE logs"
```

---

### Task 6: K8s and CI routers + background workers

**Files:**
- Modify: `daemon/routers/k8s.py`
- Modify: `daemon/routers/ci.py`
- Create: `daemon/background.py`
- Modify: `daemon/main.py`

- [ ] **Step 1: Implement k8s router**

`daemon/routers/k8s.py`:
```python
import subprocess, json
from fastapi import APIRouter, Depends
from daemon.auth import require_token
from daemon.config import CONFIG

router = APIRouter(prefix="/k8s", tags=["k8s"])

# In-memory cache refreshed by background worker
_pod_cache = {"dev": [], "prod": [], "available": True, "error": None}

def refresh_pods():
    cmd = CONFIG["kubectl_cmd"]
    for ns in ["dev", "prod"]:
        try:
            out = subprocess.check_output(
                f"{cmd} get pods -n {ns} -o json",
                shell=True, timeout=10, stderr=subprocess.DEVNULL
            )
            items = json.loads(out)["items"]
            _pod_cache[ns] = [
                {
                    "name": p["metadata"]["name"],
                    "status": p["status"]["phase"],
                    "ready": all(
                        c["ready"] for c in p["status"].get("containerStatuses", [])
                    ),
                }
                for p in items
            ]
            _pod_cache["available"] = True
            _pod_cache["error"] = None
        except Exception as e:
            _pod_cache["available"] = False
            _pod_cache["error"] = str(e)

@router.get("")
async def pod_health(_=Depends(require_token)):
    return _pod_cache
```

- [ ] **Step 2: Implement ci router**

`daemon/routers/ci.py`:
```python
import httpx
from fastapi import APIRouter, Depends
from daemon.auth import require_token
from daemon.config import CONFIG

router = APIRouter(prefix="/ci", tags=["ci"])

_ci_cache: list = []

async def refresh_ci(repos: list[str]):
    """repos: list of 'owner/repo' strings"""
    results = []
    headers = {"Authorization": f"token {CONFIG['gitea_token']}"}
    async with httpx.AsyncClient(base_url=CONFIG["gitea_url"], timeout=10) as client:
        for repo in repos:
            try:
                r = await client.get(f"/api/v1/repos/{repo}/actions/runs?limit=1", headers=headers)
                runs = r.json().get("workflow_runs", [])
                status = runs[0]["status"] if runs else "unknown"
                results.append({"repo": repo, "status": status})
            except Exception:
                results.append({"repo": repo, "status": "error"})
    return results

@router.get("")
async def ci_status(_=Depends(require_token)):
    return _ci_cache
```

- [ ] **Step 3: Implement background.py**

`daemon/background.py`:
```python
import asyncio, aiosqlite
from daemon.database import DB_PATH
from daemon.process_manager import process_manager
from daemon.routers.k8s import refresh_pods
from daemon.routers.ci import refresh_ci, _ci_cache

async def health_check_loop():
    """Every 5s: check running processes for crashes."""
    while True:
        await asyncio.sleep(5)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT id, status FROM projects WHERE status='running'") as cur:
                    rows = [dict(r) async for r in cur]
                for row in rows:
                    if not process_manager.is_running(row["id"]):
                        await db.execute(
                            "UPDATE projects SET status='error', process_pid=NULL WHERE id=?",
                            (row["id"],)
                        )
                await db.commit()
        except Exception:
            pass

async def infra_refresh_loop():
    """Every 60s: refresh K8s pods and Gitea CI."""
    while True:
        await asyncio.sleep(60)
        try:
            refresh_pods()
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT gitea_repo FROM projects WHERE gitea_repo IS NOT NULL") as cur:
                    repos = [r[0] async for r in cur]
            results = await refresh_ci(repos)
            _ci_cache.clear()
            _ci_cache.extend(results)
        except Exception:
            pass
```

- [ ] **Step 4: Wire background workers into main.py lifespan**

Update `daemon/main.py` lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await init_db(db)
    # Validate kubectl on startup
    import subprocess
    k8s_ok = True
    try:
        subprocess.check_output(
            f"{CONFIG['kubectl_cmd']} version --client",
            shell=True, timeout=5, stderr=subprocess.DEVNULL
        )
    except Exception:
        k8s_ok = False

    from daemon.background import health_check_loop, infra_refresh_loop
    tasks = [
        asyncio.create_task(health_check_loop()),
        asyncio.create_task(infra_refresh_loop()),
    ]
    app.state.k8s_available = k8s_ok
    yield
    for t in tasks:
        t.cancel()
```

- [ ] **Step 5: Update /status endpoint**

```python
@app.get("/status")
async def status(request: Request):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM projects WHERE status='running'") as cur:
            running = (await cur.fetchone())[0]
    return {
        "ok": True,
        "projects_running": running,
        "k8s_available": getattr(request.app.state, "k8s_available", False),
        "gitea_available": True,
        "warnings": [] if request.app.state.k8s_available else ["kubectl not available — check kubectl_cmd in config.json"]
    }
```

- [ ] **Step 6: Run all daemon tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 7: Smoke test daemon manually**

```bash
cd daemon && python main.py
# In another terminal:
curl http://localhost:7477/status
```
Expected: `{"ok": true, ...}`

- [ ] **Step 8: Commit**

```bash
git add daemon/
git commit -m "feat(daemon): K8s/CI routers, background health + infra refresh workers"
```

---

## Phase 3: Next.js Dashboard

### Task 7: Next.js project setup with coralbeef themes

**Files:**
- Create: `ui/package.json`
- Create: `ui/next.config.js`
- Create: `ui/styles/themes.css`
- Create: `ui/lib/api.ts`

- [ ] **Step 1: Initialize Next.js app**

```bash
cd /c/Users/USER/documents/development/devhub-repo
npx create-next-app@14 ui --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd ui
```

- [ ] **Step 2: Configure next.config.js**

`ui/next.config.js`:
```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.DAEMON_URL || 'http://localhost:7477'}/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
```

- [ ] **Step 3: Create .env.local**

`ui/.env.local`:
```
DAEMON_URL=http://localhost:7477
DAEMON_TOKEN=<paste token from daemon/config.json>
```

- [ ] **Step 4: Create server-side API client**

`ui/lib/api.ts`:
```typescript
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
```

- [ ] **Step 5: Create coralbeef theme CSS**

`ui/styles/themes.css`:
```css
/* Coralbeef 6-theme system */
:root, [data-theme="dark"] {
  --bg: #0f1117;
  --bg-card: #1a1d2e;
  --border: #2a2d3e;
  --text: #e2e8f0;
  --text-muted: #64748b;
  --accent: #6366f1;
  --accent-hover: #4f46e5;
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --running: #10b981;
  --stopped: #64748b;
  --deploying: #6366f1;
  --unknown: #f59e0b;
}

[data-theme="light"] {
  --bg: #f8fafc;
  --bg-card: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #94a3b8;
  --accent: #6366f1;
  --accent-hover: #4f46e5;
}

[data-theme="ocean"] {
  --bg: #0c1821;
  --bg-card: #1a2940;
  --border: #1e3a5f;
  --text: #cce7ff;
  --text-muted: #5a8ab0;
  --accent: #0ea5e9;
  --accent-hover: #0284c7;
}

[data-theme="forest"] {
  --bg: #0d1a0f;
  --bg-card: #1a2e1d;
  --border: #2d4a31;
  --text: #d4edda;
  --text-muted: #5a8a63;
  --accent: #22c55e;
  --accent-hover: #16a34a;
}

[data-theme="ember"] {
  --bg: #1a0d00;
  --bg-card: #2e1a0d;
  --border: #4a2d1a;
  --text: #fde8d0;
  --text-muted: #8a6050;
  --accent: #f97316;
  --accent-hover: #ea580c;
}

[data-theme="mono"] {
  --bg: #111111;
  --bg-card: #1c1c1c;
  --border: #333333;
  --text: #eeeeee;
  --text-muted: #888888;
  --accent: #eeeeee;
  --accent-hover: #cccccc;
}
```

- [ ] **Step 6: Update root layout**

`ui/app/layout.tsx`:
```tsx
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
      <body style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add ui/
git commit -m "feat(ui): Next.js 14 setup, coralbeef themes, server-side API client"
```

---

### Task 8: Dashboard and Projects pages

**Files:**
- Create: `ui/components/StatusBadge.tsx`
- Create: `ui/components/ProjectCard.tsx`
- Create: `ui/app/page.tsx`
- Create: `ui/app/projects/page.tsx`

- [ ] **Step 1: Create StatusBadge component**

`ui/components/StatusBadge.tsx`:
```tsx
const colors: Record<string, string> = {
  running: 'var(--running)',
  stopped: 'var(--stopped)',
  error: 'var(--error)',
  deploying: 'var(--deploying)',
  unknown: 'var(--unknown)',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{
      background: colors[status] || 'var(--stopped)',
      color: '#fff',
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'uppercase',
    }}>
      {status}
    </span>
  )
}
```

- [ ] **Step 2: Create ProjectCard component**

`ui/components/ProjectCard.tsx`:
```tsx
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
      <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{project.path}</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <form action={`/api/projects/${project.id}/start`} method="POST">
          <button type="submit" style={btnStyle('#10b981')}>Start</button>
        </form>
        <form action={`/api/projects/${project.id}/stop`} method="POST">
          <button type="submit" style={btnStyle('#ef4444')}>Stop</button>
        </form>
        {project.k3s_app_name && (
          <form action={`/api/projects/${project.id}/deploy`} method="POST">
            <button type="submit" style={btnStyle('var(--accent)')}>Deploy</button>
          </form>
        )}
        {project.port && (
          <a href={`http://localhost:${project.port}`} target="_blank"
             style={{ ...btnStyle('var(--text-muted)'), textDecoration: 'none' }}>
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
```

- [ ] **Step 3: Create Dashboard page**

`ui/app/page.tsx`:
```tsx
import { getStatus, getK8s } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function DashboardPage() {
  const [status, k8s] = await Promise.all([getStatus(), getK8s()])
  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>DevHub</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        <SummaryCard label="Projects Running" value={status.projects_running} color="var(--running)" />
        <SummaryCard label="K8s Available" value={status.k8s_available ? 'Yes' : 'No'}
          color={status.k8s_available ? 'var(--running)' : 'var(--error)'} />
        <SummaryCard label="Warnings" value={status.warnings.length}
          color={status.warnings.length > 0 ? 'var(--warning)' : 'var(--running)'} />
      </div>
      {status.warnings.length > 0 && (
        <div style={{ background: 'var(--warning)', color: '#000', borderRadius: 6, padding: 12, marginBottom: 24 }}>
          {status.warnings.map((w: string, i: number) => <div key={i}>{w}</div>)}
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <PodSummary namespace="dev" pods={k8s.dev} />
        <PodSummary namespace="prod" pods={k8s.prod} />
      </div>
    </main>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: any; color: string }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  )
}

function PodSummary({ namespace, pods }: { namespace: string; pods: any[] }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
        {namespace}
      </h2>
      {pods.length === 0
        ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No pods</div>
        : pods.map((p: any) => (
          <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0',
            borderBottom: '1px solid var(--border)', fontSize: 13 }}>
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
```

- [ ] **Step 4: Create Projects page**

`ui/app/projects/page.tsx`:
```tsx
import { getProjects } from '@/lib/api'
import { ProjectCard } from '@/components/ProjectCard'

export const dynamic = 'force-dynamic'

export default async function ProjectsPage() {
  const projects = await getProjects()
  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Projects</h1>
      {projects.length === 0
        ? <div style={{ color: 'var(--text-muted)' }}>No projects yet. Add one via the tray menu.</div>
        : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
            {projects.map((p: any) => <ProjectCard key={p.id} project={p} />)}
          </div>
      }
    </main>
  )
}
```

- [ ] **Step 5: Run Next.js dev server against live daemon**

```bash
cd ui && npm run dev
# Open http://localhost:3000
```
Expected: Dashboard loads showing daemon status, projects page shows empty state.

- [ ] **Step 6: Commit**

```bash
git add ui/
git commit -m "feat(ui): dashboard summary cards, projects page with ProjectCard"
```

---

### Task 9: Logs and Infrastructure pages

**Files:**
- Create: `ui/components/LogViewer.tsx`
- Create: `ui/components/PodTable.tsx`
- Create: `ui/app/logs/[id]/page.tsx`
- Create: `ui/app/infrastructure/page.tsx`

- [ ] **Step 1: Create LogViewer (client component)**

`ui/components/LogViewer.tsx`:
```tsx
'use client'
import { useEffect, useRef, useState } from 'react'

export function LogViewer({ projectId }: { projectId: string }) {
  const [lines, setLines] = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const es = new EventSource(`/api/projects/${projectId}/logs`)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setLines(prev => [...prev.slice(-499), data.line])
    }
    return () => es.close()
  }, [projectId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: 16,
      fontFamily: 'monospace',
      fontSize: 13,
      height: '70vh',
      overflowY: 'auto',
    }}>
      {lines.length === 0
        ? <span style={{ color: 'var(--text-muted)' }}>No logs yet...</span>
        : lines.map((l, i) => <div key={i} style={{ lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{l}</div>)
      }
      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 2: Create logs page**

`ui/app/logs/[id]/page.tsx`:
```tsx
import { LogViewer } from '@/components/LogViewer'

export default function LogsPage({ params }: { params: { id: string } }) {
  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Logs</h1>
      <LogViewer projectId={params.id} />
    </main>
  )
}
```

- [ ] **Step 3: Create PodTable component**

`ui/components/PodTable.tsx`:
```tsx
export function PodTable({ namespace, pods }: { namespace: string; pods: any[] }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase',
        color: 'var(--text-muted)' }}>{namespace}</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Pod</th>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Phase</th>
            <th style={{ textAlign: 'left', padding: '8px 0' }}>Ready</th>
          </tr>
        </thead>
        <tbody>
          {pods.map((p: any) => (
            <tr key={p.name} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '8px 0' }}>{p.name}</td>
              <td style={{ padding: '8px 0' }}>{p.status}</td>
              <td style={{ padding: '8px 0', color: p.ready ? 'var(--running)' : 'var(--error)' }}>
                {p.ready ? '✓' : '✗'}
              </td>
            </tr>
          ))}
          {pods.length === 0 && (
            <tr><td colSpan={3} style={{ padding: '8px 0', color: 'var(--text-muted)' }}>No pods</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Create infrastructure page**

`ui/app/infrastructure/page.tsx`:
```tsx
import { getK8s } from '@/lib/api'
import { PodTable } from '@/components/PodTable'

export const dynamic = 'force-dynamic'

export default async function InfrastructurePage() {
  const k8s = await getK8s()
  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Infrastructure</h1>
      {!k8s.available && (
        <div style={{ background: 'var(--error)', color: '#fff', borderRadius: 6, padding: 12, marginBottom: 24 }}>
          K8s unavailable: {k8s.error}
        </div>
      )}
      <PodTable namespace="dev" pods={k8s.dev} />
      <PodTable namespace="prod" pods={k8s.prod} />
    </main>
  )
}
```

- [ ] **Step 5: Add nav to layout**

Update `ui/app/layout.tsx` body to include a simple nav:
```tsx
<body style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh' }}>
  <nav style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
    padding: '12px 32px', display: 'flex', gap: 24, fontSize: 14 }}>
    <a href="/" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>DevHub</a>
    <a href="/projects" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Projects</a>
    <a href="/infrastructure" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Infrastructure</a>
  </nav>
  {children}
</body>
```

- [ ] **Step 6: Build and verify**

```bash
cd ui && npm run build
```
Expected: Build completes without errors.

- [ ] **Step 7: Commit**

```bash
git add ui/
git commit -m "feat(ui): logs SSE viewer, infrastructure pod table, nav"
```

---

## Phase 4: C# WinForms Tray App

### Task 10: Project scaffold and process manager

**Files:**
- Create: `tray/DevHub.sln`
- Create: `tray/DevHub/DevHub.csproj`
- Create: `tray/DevHub/ProcessManager.cs`
- Create: `tray/DevHub/Models/DaemonStatus.cs`

- [ ] **Step 1: Create .NET project**

```bash
cd tray
dotnet new winforms -n DevHub -f net8.0-windows
dotnet new sln -n DevHub
dotnet sln add DevHub/DevHub.csproj

# Add NuGet packages
cd DevHub
dotnet add package Microsoft.Toolkit.Uwp.Notifications
dotnet add package System.Text.Json
```

- [ ] **Step 2: Create models**

`tray/DevHub/Models/DaemonStatus.cs`:
```csharp
namespace DevHub.Models;

public record DaemonStatus(
    bool Ok,
    int ProjectsRunning,
    bool K8sAvailable,
    bool GiteaAvailable,
    string[] Warnings
);

public record Project(
    string Id,
    string Name,
    string Path,
    string Type,
    string Status,
    int? Port,
    string? K3sAppName,
    int? ProcessPid
);
```

- [ ] **Step 3: Implement ProcessManager.cs**

`tray/DevHub/ProcessManager.cs`:
```csharp
using System.Diagnostics;

namespace DevHub;

public class ProcessManager
{
    private Process? _daemon;
    private Process? _caddy;
    private Process? _ui;
    private readonly string _devhubRoot;

    public ProcessManager(string devhubRoot) => _devhubRoot = devhubRoot;

    public void StartAll(int uiPort)
    {
        _daemon = StartProcess("python", $"\"{Path.Combine(_devhubRoot, "daemon", "main.py")}\"", _devhubRoot);
        _caddy = StartProcess("caddy", $"run --config \"{Path.Combine(_devhubRoot, "Caddyfile")}\"", _devhubRoot);
        _ui = StartProcess("npm", $"run start -- --port {uiPort}", Path.Combine(_devhubRoot, "ui"));
    }

    public void StopAll()
    {
        foreach (var p in new[] { _ui, _caddy, _daemon })
            TryKill(p);
    }

    public bool IsDaemonAlive() => _daemon is { HasExited: false };
    public bool IsCaddyAlive() => _caddy is { HasExited: false };
    public bool IsUiAlive() => _ui is { HasExited: false };

    private static Process StartProcess(string exe, string args, string workDir)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            WorkingDirectory = workDir,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = false,
        };
        return Process.Start(psi) ?? throw new Exception($"Failed to start {exe}");
    }

    private static void TryKill(Process? p)
    {
        try { p?.Kill(entireProcessTree: true); } catch { }
    }

    public (bool daemon, bool caddy, bool ui) GetStatus() =>
        (IsDaemonAlive(), IsCaddyAlive(), IsUiAlive());
}
```

- [ ] **Step 4: Commit**

```bash
git add tray/
git commit -m "feat(tray): .NET 8 WinForms scaffold, ProcessManager"
```

---

### Task 11: Daemon HTTP client and config loading

**Files:**
- Create: `tray/DevHub/DaemonClient.cs`
- Create: `tray/DevHub/AppConfig.cs`

- [ ] **Step 1: Implement AppConfig**

`tray/DevHub/AppConfig.cs`:
```csharp
using System.Text.Json;
using System.Text.Json.Serialization;

namespace DevHub;

public class AppConfig
{
    [JsonPropertyName("daemon_token")] public string DaemonToken { get; set; } = "";
    [JsonPropertyName("ui_port")] public int UiPort { get; set; } = 3000;
    [JsonPropertyName("gitea_url")] public string GiteaUrl { get; set; } = "";

    public static AppConfig Load(string devhubRoot)
    {
        var path = Path.Combine(devhubRoot, "daemon", "config.json");
        if (!File.Exists(path)) return new AppConfig();
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<AppConfig>(json) ?? new AppConfig();
    }
}
```

- [ ] **Step 2: Implement DaemonClient**

`tray/DevHub/DaemonClient.cs`:
```csharp
using System.Net.Http.Headers;
using System.Text.Json;
using DevHub.Models;

namespace DevHub;

public class DaemonClient : IDisposable
{
    private readonly HttpClient _http;
    private static readonly JsonSerializerOptions _opts = new() { PropertyNameCaseInsensitive = true };

    public DaemonClient(string token)
    {
        _http = new HttpClient { BaseAddress = new Uri("http://localhost:7477/") };
        _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        _http.Timeout = TimeSpan.FromSeconds(5);
    }

    public async Task<DaemonStatus?> GetStatusAsync()
    {
        try
        {
            var json = await _http.GetStringAsync("status");
            return JsonSerializer.Deserialize<DaemonStatus>(json, _opts);
        }
        catch { return null; }
    }

    public async Task<List<Project>> GetProjectsAsync()
    {
        try
        {
            var json = await _http.GetStringAsync("projects");
            return JsonSerializer.Deserialize<List<Project>>(json, _opts) ?? [];
        }
        catch { return []; }
    }

    public async Task<bool> StartProjectAsync(string id)
    {
        try { var r = await _http.PostAsync($"projects/{id}/start", null); return r.IsSuccessStatusCode; }
        catch { return false; }
    }

    public async Task<bool> StopProjectAsync(string id)
    {
        try { var r = await _http.PostAsync($"projects/{id}/stop", null); return r.IsSuccessStatusCode; }
        catch { return false; }
    }

    public async Task<bool> DeployProjectAsync(string id)
    {
        try { var r = await _http.PostAsync($"projects/{id}/deploy", null); return r.IsSuccessStatusCode; }
        catch { return false; }
    }

    public void Dispose() => _http.Dispose();
}
```

- [ ] **Step 3: Commit**

```bash
git add tray/
git commit -m "feat(tray): DaemonClient HTTP wrapper, AppConfig loader"
```

---

### Task 12: TrayApp — icon, menu, polling

**Files:**
- Create: `tray/DevHub/TrayApp.cs`
- Create: `tray/DevHub/StartupHelper.cs`
- Create: `tray/DevHub/ToastHelper.cs`
- Modify: `tray/DevHub/Program.cs`

- [ ] **Step 1: Implement StartupHelper**

`tray/DevHub/StartupHelper.cs`:
```csharp
using Microsoft.Win32;

namespace DevHub;

public static class StartupHelper
{
    private const string KeyPath = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Run";
    private const string ValueName = "DevHub";

    public static void Enable(string exePath)
    {
        using var key = Registry.CurrentUser.OpenSubKey(KeyPath, true);
        key?.SetValue(ValueName, $"\"{exePath}\"");
    }

    public static void Disable()
    {
        using var key = Registry.CurrentUser.OpenSubKey(KeyPath, true);
        key?.DeleteValue(ValueName, false);
    }
}
```

- [ ] **Step 2: Implement ToastHelper**

`tray/DevHub/ToastHelper.cs`:
```csharp
using Microsoft.Toolkit.Uwp.Notifications;

namespace DevHub;

public static class ToastHelper
{
    public static void Notify(string title, string message)
    {
        try
        {
            new ToastContentBuilder()
                .AddText(title)
                .AddText(message)
                .Show();
        }
        catch { /* Toast not available in all Windows versions */ }
    }
}
```

- [ ] **Step 3: Implement TrayApp**

`tray/DevHub/TrayApp.cs`:
```csharp
using DevHub.Models;
using System.Diagnostics;

namespace DevHub;

public class TrayApp : ApplicationContext
{
    private readonly NotifyIcon _tray;
    private readonly ProcessManager _processes;
    private readonly DaemonClient _client;
    private readonly System.Windows.Forms.Timer _timer;
    private readonly string _devhubRoot;
    private int _backoffMs = 250;
    private bool _daemonReady = false;

    public TrayApp(string devhubRoot)
    {
        _devhubRoot = devhubRoot;
        var config = AppConfig.Load(devhubRoot);

        _processes = new ProcessManager(devhubRoot);
        _client = new DaemonClient(config.DaemonToken);

        _tray = new NotifyIcon
        {
            Icon = SystemIcons.Application,
            Text = "DevHub",
            Visible = true,
            ContextMenuStrip = BuildMenu([]),
        };

        _timer = new System.Windows.Forms.Timer { Interval = 250 };
        _timer.Tick += OnTick;
        _timer.Start();

        _processes.StartAll(config.UiPort);
    }

    private async void OnTick(object? sender, EventArgs e)
    {
        _timer.Stop();

        if (!_daemonReady)
        {
            // Backoff polling until daemon is up
            var status = await _client.GetStatusAsync();
            if (status != null)
            {
                _daemonReady = true;
                _timer.Interval = 5000;
                ToastHelper.Notify("DevHub", "Dev hub is ready.");
            }
            else
            {
                _backoffMs = Math.Min(_backoffMs * 2, 2000);
                _timer.Interval = _backoffMs;
            }
        }
        else
        {
            await RefreshAsync();
        }

        _timer.Start();
    }

    private async Task RefreshAsync()
    {
        var projects = await _client.GetProjectsAsync();
        var status = await _client.GetStatusAsync();

        // Check for crashes in managed processes
        var (daemon, caddy, ui) = _processes.GetStatus();
        if (!daemon) { _processes.StartAll(AppConfig.Load(_devhubRoot).UiPort); ToastHelper.Notify("DevHub", "Daemon crashed — restarting."); }

        _tray.Icon = (status?.Warnings?.Length > 0) ? SystemIcons.Warning : SystemIcons.Application;
        _tray.ContextMenuStrip = BuildMenu(projects);
    }

    private ContextMenuStrip BuildMenu(List<Project> projects)
    {
        var menu = new ContextMenuStrip();

        menu.Items.Add("Open Dashboard", null, (_, _) =>
            Process.Start(new ProcessStartInfo("http://devhub.localhost") { UseShellExecute = true }));

        menu.Items.Add(new ToolStripSeparator());

        foreach (var p in projects)
        {
            var sub = new ToolStripMenuItem($"{p.Name}  [{p.Status}]");
            sub.DropDownItems.Add("Start", null, async (_, _) => await _client.StartProjectAsync(p.Id));
            sub.DropDownItems.Add("Stop", null, async (_, _) => await _client.StopProjectAsync(p.Id));
            if (p.K3sAppName != null)
                sub.DropDownItems.Add("Deploy to dev", null, async (_, _) => await _client.DeployProjectAsync(p.Id));
            if (p.Port.HasValue)
                sub.DropDownItems.Add("Open in browser", null, (_, _) =>
                    Process.Start(new ProcessStartInfo($"http://localhost:{p.Port}") { UseShellExecute = true }));
            menu.Items.Add(sub);
        }

        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("Run at Startup", null, (_, _) =>
            StartupHelper.Enable(Application.ExecutablePath));

        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("Quit", null, (_, _) =>
        {
            _processes.StopAll();
            _tray.Visible = false;
            Application.Exit();
        });

        return menu;
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) { _tray.Dispose(); _timer.Dispose(); _client.Dispose(); }
        base.Dispose(disposing);
    }
}
```

- [ ] **Step 4: Update Program.cs**

`tray/DevHub/Program.cs`:
```csharp
using DevHub;

// Single-instance check
var mutex = new Mutex(true, "DevHub_SingleInstance", out var isNew);
if (!isNew)
{
    MessageBox.Show("DevHub is already running.", "DevHub", MessageBoxButtons.OK, MessageBoxIcon.Information);
    return;
}

Application.EnableVisualStyles();
Application.SetCompatibleTextRenderingDefault(false);

// In release zip: DevHub.exe sits at the root alongside daemon\ and ui\
// AppContext.BaseDirectory is the directory containing the exe, which IS the root.
// In dev (bin/Release/net8.0-windows/win-x64/publish/), set DEVHUB_ROOT env var to override.
var root = Environment.GetEnvironmentVariable("DEVHUB_ROOT")
    ?? AppContext.BaseDirectory;
Application.Run(new TrayApp(root));

mutex.ReleaseMutex();
```

- [ ] **Step 5: Build and test**

```bash
cd tray
dotnet build DevHub/DevHub.csproj -c Release
```
Expected: Build succeeds with no errors.

- [ ] **Step 6: Run tray app with daemon running**

Start the daemon first:
```bash
cd daemon && python main.py
```
Then run the tray:
```bash
cd tray && dotnet run --project DevHub
```
Expected: Tray icon appears in system tray, daemon connects, menu shows "Open Dashboard".

- [ ] **Step 7: Commit**

```bash
git add tray/
git commit -m "feat(tray): system tray app, polling loop, project menu, startup registry"
```

---

## Phase 5: CI/CD and Release

### Task 13: GitHub Actions + Gitea CI

**Files:**
- Create: `.github/workflows/build.yml`
- Create: `.gitea/workflows/build.yml`

- [ ] **Step 1: Create both CI workflow files**

`.github/workflows/build.yml` and `.gitea/workflows/build.yml` (identical content — Gitea Actions uses the same syntax):
```yaml
name: Build

on:
  push:
    branches: [main]
  release:
    types: [created]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build tray exe
        run: |
          cd tray
          dotnet publish DevHub/DevHub.csproj -c Release -r win-x64 --self-contained -o ../dist/tray

      - name: Build Next.js dashboard
        run: |
          cd ui
          npm ci
          npm run build

      - name: Package release zip
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force dist/release | Out-Null
          Copy-Item dist/tray/DevHub.exe dist/release/
          Copy-Item Caddyfile dist/release/
          Copy-Item daemon dist/release/daemon -Recurse
          Copy-Item ui/.next dist/release/ui/.next -Recurse
          Copy-Item ui/public dist/release/ui/public -Recurse
          Copy-Item ui/package.json dist/release/ui/
          Compress-Archive -Path dist/release/* -DestinationPath opalproxima-windows.zip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: opalproxima-windows
          path: opalproxima-windows.zip

      - name: Upload release asset
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: opalproxima-windows.zip
```

Note: save the same content to both `.github/workflows/build.yml` and `.gitea/workflows/build.yml`.

- [ ] **Step 2: Mirror to Gitea and push**

```bash
git add .github/ .gitea/
git commit -m "ci: GitHub Actions + Gitea Actions build, package release zip"
git push origin main
gitea-mirror antoinemassih/opalproxima-windows
```

- [ ] **Step 3: Verify CI runs on Gitea**

```bash
# Check Gitea Actions
open http://192.168.1.42:3000/antoine/opalproxima-windows/actions
```
Expected: Build job appears and runs.

---

## Phase 6: Final Integration Test

### Task 14: End-to-end smoke test

- [ ] **Step 1: Start everything manually**

```bash
# Terminal 1 — daemon
cd /c/Users/USER/devhub/daemon && python main.py

# Terminal 2 — UI
cd /c/Users/USER/devhub/ui && npm run start

# Terminal 3 — Caddy
cd /c/Users/USER/devhub && ./caddy.exe run --config Caddyfile

# Terminal 4 — Tray (or run built exe)
cd /c/Users/USER/devhub/tray && dotnet run --project DevHub
```

- [ ] **Step 2: Verify dashboard loads**

Open `http://devhub.localhost` — dashboard shows, no auth errors.

- [ ] **Step 3: Add a test project via API**

```bash
curl -X POST http://localhost:7477/projects \
  -H "Authorization: Bearer $(cat daemon/config.json | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"daemon_token\"])')" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "path": "C:/Users/USER/documents/development"}'
```
Expected: Project appears in `/projects` response and in tray menu.

- [ ] **Step 4: Verify tray menu shows project**

Right-click tray icon → project "test" appears with Start/Stop submenus.

- [ ] **Step 5: Final commit and tag**

```bash
git add .
git commit -m "chore: final integration verified"
git tag v0.1.0
git push origin main --tags
```
Expected: GitHub Actions runs, produces `opalproxima-windows.zip` release artifact.
