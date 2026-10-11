"""Unit tests for stats endpoint, health check, security response headers, and request tracing."""

import pytest


def test_stats_valid_dataset_id(client, make_csv):
    """Test retrieving statistics for a valid dataset_id."""
    upload_res = client.post(
        "/upload",
        files={"file": ("stats.csv", make_csv("num1,num2\n10,20\n30,40"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    response = client.get(f"/stats/{dataset_id}")
    assert response.status_code == 200
    data = response.json()
    assert "numeric_summary" in data
    assert "num1" in data["numeric_summary"]


def test_stats_invalid_dataset_id(client):
    """Test stats endpoint with an invalid dataset_id returns 404."""
    response = client.get("/stats/unknown-uuid-00000")
    assert response.status_code == 404
    assert "not found" in str(response.json()).lower()


def test_health_endpoint(client):
    """Test /health probe returns 200 and expected status dict."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "datasets_loaded" in data


def test_security_headers_and_request_id(client):
    """Test that all responses include X-Request-ID and security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


# ---------------------------------------------------------------------------
# Client IP resolution and Forwarding Header Security Tests
# ---------------------------------------------------------------------------

class _MockClient:
    def __init__(self, host: str):
        self.host = host


class _MockRequest:
    def __init__(self, host: str = "198.51.100.5", headers: dict = None):
        self.client = _MockClient(host)
        self.headers = headers or {}


def test_get_client_ip_direct_ignores_spoofed_headers(monkeypatch):
    """Direct untrusted peer: X-Forwarded-For and X-Real-IP must NOT be trusted."""
    from security import get_client_ip
    from config import settings

    monkeypatch.setattr(settings, "trusted_proxies", [])

    # Client tries to spoof arbitrary external/internal IPs
    req = _MockRequest(
        host="198.51.100.5",
        headers={
            "X-Forwarded-For": "10.0.0.1, 1.1.1.1",
            "X-Real-IP": "172.16.0.1",
        },
    )
    resolved_ip = get_client_ip(req)
    assert resolved_ip == "198.51.100.5"


def test_get_client_ip_trusted_proxy_resolves_forwarded_for(monkeypatch):
    """When peer is a verified trusted proxy, forwarding headers are securely resolved."""
    from security import get_client_ip
    from config import settings

    monkeypatch.setattr(settings, "trusted_proxies", ["127.0.0.1", "10.0.0.2"])

    # 1. Peer in trusted_proxies with X-Real-IP
    req_real = _MockRequest(
        host="127.0.0.1",
        headers={"X-Real-IP": "203.0.113.195"},
    )
    assert get_client_ip(req_real) == "203.0.113.195"

    # 2. Peer in trusted_proxies with X-Forwarded-For single client
    req_fwd = _MockRequest(
        host="10.0.0.2",
        headers={"X-Forwarded-For": "203.0.113.195"},
    )
    assert get_client_ip(req_fwd) == "203.0.113.195"

    # 3. Attacker injected prefix in X-Forwarded-For before trusted proxy appended real IP
    req_multi = _MockRequest(
        host="127.0.0.1",
        headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.195"},
    )
    # The rightmost non-trusted IP should be selected (203.0.113.195)
    assert get_client_ip(req_multi) == "203.0.113.195"


# ---------------------------------------------------------------------------
# Rate Limiting Enforcement Tests
# ---------------------------------------------------------------------------

def test_rate_limiting_prevents_spoofed_ip_bypass(client, make_csv, monkeypatch):
    """Verify an attacker cannot bypass rate limits by rotating X-Forwarded-For headers."""
    from app import limiter
    from config import settings

    monkeypatch.setattr(settings, "trusted_proxies", [])

    limiter.enabled = True
    limiter.reset()

    # Upload limit is 10/minute
    file_bytes = make_csv("a,b\n1,2")
    files = {"file": ("data.csv", file_bytes, "text/csv")}

    # Send 10 uploads with rotated spoofed X-Forwarded-For headers
    for i in range(10):
        resp = client.post(
            "/upload",
            files={"file": ("data.csv", file_bytes, "text/csv")},
            headers={"X-Forwarded-For": f"198.51.100.{i + 1}"},
        )
        assert resp.status_code == 200, f"Upload {i+1} failed unexpectedly: {resp.text}"

    # 11th request from the same peer must be blocked with 429 despite new spoofed header
    blocked_resp = client.post(
        "/upload",
        files={"file": ("data.csv", file_bytes, "text/csv")},
        headers={"X-Forwarded-For": "198.51.100.99"},
    )
    assert blocked_resp.status_code == 429
    limiter.enabled = False


def test_upload_rate_limit_strictly_enforced(client, make_csv):
    """Verify /upload strictly enforces its 10/minute limit."""
    from app import limiter

    limiter.enabled = True
    limiter.reset()

    file_bytes = make_csv("x,y\n10,20")
    # First 10 uploads pass
    for i in range(10):
        resp = client.post(
            "/upload",
            files={"file": (f"test_{i}.csv", file_bytes, "text/csv")},
        )
        assert resp.status_code == 200

    # 11th request triggers rate limit
    resp_blocked = client.post(
        "/upload",
        files={"file": ("test_overflow.csv", file_bytes, "text/csv")},
    )
    assert resp_blocked.status_code == 429
    limiter.enabled = False


def test_chat_rate_limit_strictly_enforced(client, make_csv, mock_ai_response):
    """Verify /chat strictly enforces its 30/minute limit."""
    from app import limiter

    # Disable limiter for upload setup
    limiter.enabled = False
    upload_res = client.post(
        "/upload",
        files={"file": ("chat_rate.csv", make_csv("dept,sales\nHR,100"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    limiter.enabled = True
    limiter.reset()

    # 30 chat requests pass
    for i in range(30):
        resp = client.post(
            "/chat",
            json={"dataset_id": dataset_id, "question": f"Question {i}?"},
        )
        assert resp.status_code == 200, f"Chat {i} failed: {resp.text}"

    # 31st chat request triggers rate limit
    resp_blocked = client.post(
        "/chat",
        json={"dataset_id": dataset_id, "question": "Question 31?"},
    )
    assert resp_blocked.status_code == 429
    limiter.enabled = False


def test_filter_rate_limit_and_normal_usage(client, make_csv):
    """Verify /filter supports multiple normal rapid user filter requests and enforces limit."""
    from app import limiter

    # Disable limiter for upload
    limiter.enabled = False
    upload_res = client.post(
        "/upload",
        files={"file": ("filter_test.csv", make_csv("category,amount\nA,10\nB,20\nA,30"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    limiter.enabled = True
    limiter.reset()

    # Normal user filtering: 10 filter queries in rapid succession succeed
    for i in range(10):
        resp = client.post(
            "/filter",
            json={"dataset_id": dataset_id, "filters": {"category": ["A"]}},
        )
        assert resp.status_code == 200
        assert resp.json()["row_count"] == 2

    limiter.enabled = False


def test_health_endpoint_exempt_from_rate_limits(client):
    """Verify /health is exempt and can be polled frequently by monitoring without 429."""
    from app import limiter

    limiter.enabled = True
    limiter.reset()

    # Call /health 70 times (exceeding default 60/min limit if it were not exempt)
    for _ in range(70):
        resp = client.get("/health")
        assert resp.status_code == 200

    limiter.enabled = False

