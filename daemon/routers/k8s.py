from fastapi import APIRouter, Depends
from daemon.auth import require_token
router = APIRouter(prefix="/k8s", tags=["k8s"])

@router.get("")
async def pod_health(_=Depends(require_token)):
    return {"dev": [], "prod": [], "available": False, "error": "Not yet implemented"}
