import pytest
from unittest.mock import patch, MagicMock
from daemon.process_manager import ProcessManager

def test_start_records_pid():
    pm = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    mock_proc.poll.return_value = None  # process still running
    mock_proc.stdout = iter([])  # empty stdout
    with patch("daemon.process_manager.subprocess.Popen", return_value=mock_proc):
        pid = pm.start("proj1", "echo hello", "C:/tmp")
    assert pid == 1234
    assert pm.is_running("proj1")

def test_stop_sends_ctrl_break():
    pm = ProcessManager()
    mock_proc = MagicMock()
    mock_proc.pid = 5678
    mock_proc.stdout = iter([])
    with patch("daemon.process_manager.subprocess.Popen", return_value=mock_proc):
        pm.start("proj1", "echo hello", "C:/tmp")
    pm.stop("proj1")
    mock_proc.send_signal.assert_called_once()

def test_is_running_false_when_not_started():
    pm = ProcessManager()
    assert not pm.is_running("nonexistent")
