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
