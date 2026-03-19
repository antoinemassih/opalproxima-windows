import httpx
from fastapi import APIRouter, Depends
from daemon.auth import require_token
from daemon.config import CONFIG

router = APIRouter(prefix="/ci", tags=["ci"])

_ci_cache: list = []

async def refresh_ci(repos: list[str]):
    """repos: list of 'owner/repo' strings from Gitea."""
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
