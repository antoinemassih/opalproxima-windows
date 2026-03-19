import json, secrets
from pathlib import Path

DEFAULTS = {
    "daemon_token": "",
    "gitea_url": "http://192.168.1.42:3000",
    "gitea_token": "",
    "kubeconfig": "C:/Users/USER/.kube/config",
    "registry": "192.168.1.71:5000",
    "kubectl_cmd": "wsl kubectl",
    "k3s_app_cmd": "wsl k3s-app",
    "ui_port": 3000,
}

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config(path: Path = Path(__file__).parent / "config.json") -> dict:
    cfg = {**DEFAULTS}
    if path.exists():
        cfg.update(json.loads(path.read_text()))
    if not cfg["daemon_token"]:
        cfg["daemon_token"] = secrets.token_hex(32)
        path.write_text(json.dumps(cfg, indent=2))
    return cfg

CONFIG = load_config(DEFAULT_CONFIG_PATH)
