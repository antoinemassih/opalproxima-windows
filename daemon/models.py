from pydantic import BaseModel
from typing import Optional

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
