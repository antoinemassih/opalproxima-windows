import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import asyncio, json

from daemon.auth import require_token
from daemon.database import get_db
from daemon.models import ProjectCreate
from daemon.process_manager import process_manager
from daemon.log_buffer import get_buffer

router = APIRouter(prefix="/projects", tags=["projects"])

async def _get_project_or_404(db, project_id: str) -> dict:
    async with db.execute("SELECT * FROM projects WHERE id=?", (project_id,)) as cur:
        row = await cur.fetchone()
    if row is None:
        raise HTTPException(404, f"Project {project_id} not found")
    return dict(row)

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
    row = await _get_project_or_404(db, project_id)
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

@router.post("/{project_id}/deploy")
async def deploy_project(project_id: str, db=Depends(get_db), _=Depends(require_token)):
    from daemon.config import CONFIG
    import subprocess
    row = await _get_project_or_404(db, project_id)
    if not row.get("k3s_app_name"):
        raise HTTPException(400, "Project has no k3s_app_name configured")
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE projects SET status='deploying', updated_at=? WHERE id=?", (now, project_id))
    await db.commit()
    cmd = f"{CONFIG['k3s_app_cmd']} deploy {row['k3s_app_name']} {row['path']}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    status = "stopped" if result.returncode == 0 else "error"
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE projects SET status=?, updated_at=? WHERE id=?", (status, now, project_id))
    await db.commit()
    return {"ok": result.returncode == 0, "output": result.stdout, "error": result.stderr}

@router.post("/{project_id}/promote")
async def promote_project(project_id: str, db=Depends(get_db), _=Depends(require_token)):
    from daemon.config import CONFIG
    import subprocess
    row = await _get_project_or_404(db, project_id)
    if not row.get("k3s_app_name"):
        raise HTTPException(400, "Project has no k3s_app_name configured")
    cmd = f"{CONFIG['k3s_app_cmd']} promote {row['k3s_app_name']}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return {"ok": result.returncode == 0, "output": result.stdout, "error": result.stderr}

@router.get("/{project_id}/logs")
async def stream_logs(project_id: str, _=Depends(require_token)):
    buf = get_buffer(project_id)
    async def generate():
        for line in buf.lines():
            yield f"data: {json.dumps({'line': line})}\n\n"
        seen = len(buf.lines())
        while True:
            lines = buf.lines()
            for line in lines[seen:]:
                yield f"data: {json.dumps({'line': line})}\n\n"
            seen = len(lines)
            await asyncio.sleep(0.2)
    return StreamingResponse(generate(), media_type="text/event-stream")
