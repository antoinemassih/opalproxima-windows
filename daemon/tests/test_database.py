import pytest
import aiosqlite

@pytest.mark.asyncio
async def test_projects_table_created(tmp_path):
    db_path = tmp_path / "test.db"
    from daemon.database import init_db
    async with aiosqlite.connect(db_path) as db:
        await init_db(db)
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cur:
            tables = [r[0] async for r in cur]
    assert "projects" in tables
