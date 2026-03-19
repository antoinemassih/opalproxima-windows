import pytest
import daemon.config as cfg_module
from fastapi.testclient import TestClient

TOKEN = "testtoken"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setitem(cfg_module.CONFIG, "daemon_token", TOKEN)
    # Use a temp DB for each test
    import daemon.database as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from daemon.main import app
    with TestClient(app) as c:
        yield c

def test_list_projects_empty(client):
    r = client.get("/projects", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []

def test_add_project(client, tmp_path):
    r = client.post("/projects", headers=HEADERS, json={
        "name": "myapp",
        "path": str(tmp_path),
    })
    assert r.status_code == 200
    assert r.json()["name"] == "myapp"
    assert r.json()["status"] == "stopped"

def test_add_project_requires_auth(client, tmp_path):
    r = client.post("/projects", json={"name": "x", "path": str(tmp_path)})
    assert r.status_code == 401

def test_delete_project(client, tmp_path):
    r = client.post("/projects", headers=HEADERS, json={"name": "del", "path": str(tmp_path)})
    pid = r.json()["id"]
    r2 = client.delete(f"/projects/{pid}", headers=HEADERS)
    assert r2.status_code == 200
    # Verify deleted
    r3 = client.get("/projects", headers=HEADERS)
    assert all(p["id"] != pid for p in r3.json())
