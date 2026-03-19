from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
import aiosqlite

from daemon.database import init_db
import daemon.database as _db_module
from daemon.routers import projects, k8s, ci
from daemon.config import CONFIG

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB — read DB_PATH at runtime so tests can monkeypatch it
    async with aiosqlite.connect(_db_module.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await init_db(db)
    # Validate kubectl
    import subprocess
    try:
        subprocess.check_output(
            f"{CONFIG['kubectl_cmd']} version --client",
            shell=True, timeout=5, stderr=subprocess.DEVNULL
        )
        app.state.k8s_available = True
    except Exception:
        app.state.k8s_available = False

    # Start background workers
    from daemon.background import health_check_loop, infra_refresh_loop
    tasks = [
        asyncio.create_task(health_check_loop()),
        asyncio.create_task(infra_refresh_loop()),
    ]
    yield
    # Cancel background tasks on shutdown
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title="DevHub Daemon", lifespan=lifespan)
app.include_router(projects.router)
app.include_router(k8s.router)
app.include_router(ci.router)

@app.get("/status")
async def status(request: Request):
    async with aiosqlite.connect(_db_module.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM projects WHERE status='running'") as cur:
            running = (await cur.fetchone())[0]
    k8s_avail = getattr(request.app.state, "k8s_available", False)
    warnings = [] if k8s_avail else ["kubectl not available — check kubectl_cmd in config.json"]
    return {
        "ok": True,
        "projects_running": running,
        "k8s_available": k8s_avail,
        "gitea_available": True,
        "warnings": warnings,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=7477, reload=False)
