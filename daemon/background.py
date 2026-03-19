import asyncio
import aiosqlite
import daemon.database as _db_module
from daemon.process_manager import process_manager

async def health_check_loop():
    """Every 5s: check running processes for crashes, update DB."""
    while True:
        await asyncio.sleep(5)
        try:
            async with aiosqlite.connect(_db_module.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id, status FROM projects WHERE status='running'"
                ) as cur:
                    rows = [dict(r) async for r in cur]
                for row in rows:
                    if not process_manager.is_running(row["id"]):
                        await db.execute(
                            "UPDATE projects SET status='error', process_pid=NULL WHERE id=?",
                            (row["id"],)
                        )
                await db.commit()
        except Exception:
            pass  # Don't crash the loop on transient errors

async def infra_refresh_loop():
    """Every 60s: refresh K8s pods and Gitea CI."""
    while True:
        await asyncio.sleep(60)
        try:
            loop = asyncio.get_event_loop()
            from daemon.routers.k8s import refresh_pods
            await loop.run_in_executor(None, refresh_pods)
        except Exception:
            pass
        try:
            async with aiosqlite.connect(_db_module.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT gitea_repo FROM projects WHERE gitea_repo IS NOT NULL"
                ) as cur:
                    repos = [r[0] async for r in cur]
            from daemon.routers.ci import refresh_ci, _ci_cache
            results = await refresh_ci(repos)
            _ci_cache.clear()
            _ci_cache.extend(results)
        except Exception:
            pass
