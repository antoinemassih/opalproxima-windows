import subprocess, signal, threading
import psutil
from daemon.log_buffer import get_buffer, clear_buffer

class ProcessManager:
    def __init__(self):
        self._procs: dict[str, subprocess.Popen] = {}

    def start(self, project_id: str, cmd: str, cwd: str) -> int:
        clear_buffer(project_id)
        buf = get_buffer(project_id)
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            text=True,
            bufsize=1,
        )
        self._procs[project_id] = proc

        def _reader():
            for line in proc.stdout:
                buf.append(line.rstrip())

        threading.Thread(target=_reader, daemon=True).start()
        return proc.pid

    def stop(self, project_id: str):
        proc = self._procs.pop(project_id, None)
        if proc:
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def is_running(self, project_id: str) -> bool:
        proc = self._procs.get(project_id)
        if not proc:
            return False
        return proc.poll() is None

    def validate_stale_pids(self, projects: list[dict]) -> list[str]:
        """Returns IDs of projects whose stored PID is stale or belongs to a different process."""
        stale = []
        for p in projects:
            pid = p.get("process_pid")
            if pid:
                if not psutil.pid_exists(pid):
                    stale.append(p["id"])
                else:
                    # Check if PID belongs to a process we actually started
                    if p["id"] not in self._procs:
                        stale.append(p["id"])
        return stale

# Global instance
process_manager = ProcessManager()
