from daemon.log_buffer import LogBuffer

def test_buffer_stores_lines():
    buf = LogBuffer(max_lines=5)
    buf.append("line1")
    buf.append("line2")
    assert buf.lines() == ["line1", "line2"]

def test_buffer_evicts_oldest_at_max():
    buf = LogBuffer(max_lines=3)
    for i in range(5):
        buf.append(f"line{i}")
    lines = buf.lines()
    assert len(lines) == 3
    assert lines[0] == "line2"

def test_buffer_clear():
    buf = LogBuffer()
    buf.append("x")
    buf.clear()
    assert buf.lines() == []
