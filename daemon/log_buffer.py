from collections import deque
from threading import Lock

class LogBuffer:
    def __init__(self, max_lines: int = 500):
        self._buf = deque(maxlen=max_lines)
        self._lock = Lock()

    def append(self, line: str):
        with self._lock:
            self._buf.append(line)

    def lines(self) -> list[str]:
        with self._lock:
            return list(self._buf)

    def clear(self):
        with self._lock:
            self._buf.clear()

# Global registry: project_id → LogBuffer
_buffers: dict[str, LogBuffer] = {}
_registry_lock = Lock()

def get_buffer(project_id: str) -> LogBuffer:
    with _registry_lock:
        if project_id not in _buffers:
            _buffers[project_id] = LogBuffer()
        return _buffers[project_id]

def clear_buffer(project_id: str):
    with _registry_lock:
        if project_id in _buffers:
            _buffers[project_id].clear()
