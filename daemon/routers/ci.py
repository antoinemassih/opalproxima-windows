from fastapi import APIRouter, Depends
from daemon.auth import require_token
router = APIRouter(prefix="/ci", tags=["ci"])

@router.get("")
async def ci_status(_=Depends(require_token)):
    return []
