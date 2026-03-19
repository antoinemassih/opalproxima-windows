import pytest
import daemon.config as cfg_module
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from daemon.auth import require_token

app = FastAPI()

@app.get("/protected")
async def protected(token=Depends(require_token)):
    return {"ok": True}

client = TestClient(app)

def test_no_token_returns_401():
    r = client.get("/protected")
    assert r.status_code == 401

def test_wrong_token_returns_403(monkeypatch):
    # Patch CONFIG in place so auth.py sees the updated token
    monkeypatch.setitem(cfg_module.CONFIG, "daemon_token", "realtoken")
    r = client.get("/protected", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403

def test_correct_token_passes(monkeypatch):
    monkeypatch.setitem(cfg_module.CONFIG, "daemon_token", "testtoken")
    r = client.get("/protected", headers={"Authorization": "Bearer testtoken"})
    assert r.status_code == 200
