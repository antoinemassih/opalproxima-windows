import subprocess, json
from fastapi import APIRouter, Depends
from daemon.auth import require_token
from daemon.config import CONFIG

router = APIRouter(prefix="/k8s", tags=["k8s"])

# In-memory cache refreshed by background worker
_pod_cache: dict = {"dev": [], "prod": [], "available": True, "error": None}

def refresh_pods():
    """Synchronous — call from background thread via run_in_executor."""
    cmd = CONFIG["kubectl_cmd"]
    new_cache: dict = {"dev": [], "prod": [], "available": True, "error": None}
    for ns in ["dev", "prod"]:
        try:
            out = subprocess.check_output(
                f"{cmd} get pods -n {ns} -o json",
                shell=True, timeout=10, stderr=subprocess.DEVNULL
            )
            items = json.loads(out)["items"]
            new_cache[ns] = [
                {
                    "name": p["metadata"]["name"],
                    "status": p["status"]["phase"],
                    "ready": all(
                        c["ready"] for c in p["status"].get("containerStatuses", [])
                    ),
                }
                for p in items
            ]
        except Exception as e:
            new_cache["available"] = False
            new_cache["error"] = str(e)
    _pod_cache.update(new_cache)

@router.get("")
async def pod_health(_=Depends(require_token)):
    return _pod_cache
