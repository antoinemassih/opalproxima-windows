from typing import Optional
from fastapi import Header, HTTPException, Depends
from daemon.config import CONFIG

async def require_token(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization[7:]
    if token != CONFIG["daemon_token"]:
        raise HTTPException(403, "Invalid token")
    return token
