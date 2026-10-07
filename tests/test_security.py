from recondeck.security import host_allowed, origin_allowed


def test_host_allowed_accepts_loopback_with_port():
    assert host_allowed("127.0.0.1:5000", 5000) is True
    assert host_allowed("localhost:5000", 5000) is True


def test_host_allowed_rejects_missing_port_or_foreign_host():
    assert host_allowed("127.0.0.1", 5000) is False
    assert host_allowed("example.com:443", 5000) is False
    assert host_allowed("https://localhost:5000", 5000) is False


def test_origin_allowed_accepts_loopback_http_origins_only():
    assert origin_allowed("http://127.0.0.1:5000", 5000) is True
    assert origin_allowed("http://localhost:5000", 5000) is True


def test_origin_allowed_rejects_non_http_or_foreign_origins():
    assert origin_allowed("https://127.0.0.1:5000", 5000) is False
    assert origin_allowed("http://example.com:80", 5000) is False
    assert origin_allowed("http://localhost", 5000) is False
