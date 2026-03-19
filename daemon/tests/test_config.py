import json, pytest
from pathlib import Path

def test_config_generates_token_on_first_run(tmp_path):
    config_path = tmp_path / "config.json"
    from daemon.config import load_config
    cfg = load_config(config_path)
    assert len(cfg["daemon_token"]) == 64  # 32 bytes hex
    assert config_path.exists()

def test_config_reuses_existing_token(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"daemon_token": "abc123"}))
    from daemon.config import load_config
    cfg = load_config(config_path)
    assert cfg["daemon_token"] == "abc123"
