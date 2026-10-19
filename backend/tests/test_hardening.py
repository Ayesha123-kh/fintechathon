import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.middleware import BodyLimit, SecurityHeaders, body_cap
from app.services.market_data import _public_address, fetch_url
from app.services.notify import push_endpoint_ok


@pytest.mark.parametrize("url", [
    "https://fcm.googleapis.com/fcm/send/abc:def",
    "https://updates.push.services.mozilla.com/wpush/v2/gAAAA",
    "https://web.push.apple.com/QGuQyavXutnMH",
    "https://wns2-par02p.notify.windows.com/w/?token=x",
])
def test_real_push_services_are_accepted(url):
    assert push_endpoint_ok(url)


@pytest.mark.parametrize("url", [
    "http://fcm.googleapis.com/fcm/send/abc",  # not https
    "https://backend:8000/api/internal/omb/events",  # an internal service
    "https://169.254.169.254/latest/meta-data",
    "https://fcm.googleapis.com.evil.example/x",
    "https://fcm.googleapis.com:8443/x",
    "https://user:pw@fcm.googleapis.com/x",
    "not a url",
])
def test_anything_else_is_refused_as_a_push_endpoint(url):
    assert not push_endpoint_ok(url)


@pytest.mark.parametrize("host, public", [
    ("8.8.8.8", True), ("1.1.1.1", True),
    ("127.0.0.1", False), ("10.0.0.7", False), ("172.18.0.3", False), ("192.168.1.10", False),
    ("169.254.169.254", False), ("100.64.0.1", False), ("0.0.0.0", False), ("::1", False),
    ("::ffff:127.0.0.1", False), ("fd00::1", False), ("localhost", False),
])
async def test_only_public_addresses_count_as_public(host, public):
    assert await _public_address(host) is public


@pytest.mark.parametrize("url, reason", [
    ("http://127.0.0.1/", "private or internal network"),
    ("http://169.254.169.254/latest/meta-data/", "private or internal network"),
    ("http://localhost/api/health", "private or internal network"),
    ("http://8.8.8.8:6379/", "standard web ports"),
    ("file:///etc/passwd", "only http(s)"),
])
async def test_the_bots_cannot_fetch_internal_addresses(url, reason):
    assert reason in (await fetch_url(url))["error"]


async def echo(request: Request) -> JSONResponse:
    return JSONResponse({"bytes": len(await request.body())})


async def photo(request: Request) -> Response:
    return Response(b"img", headers={"Cache-Control": "private, max-age=60"})


app = SecurityHeaders(BodyLimit(Starlette(routes=[
    Route("/api/chat/messages", echo, methods=["POST"]), Route("/api/me/avatar", photo)])))


def test_bodies_over_the_cap_are_refused_whether_or_not_their_length_is_declared():
    client = TestClient(app)
    cap = body_cap("/api/chat/messages")
    assert client.post("/api/chat/messages", content=b"x" * cap).json() == {"bytes": cap}
    assert client.post("/api/chat/messages", content=b"x" * (cap + 1)).status_code == 413
    chunks = (b"x" * 16_384 for _ in range(cap // 16_384 + 2))  # streamed, no Content-Length
    assert client.post("/api/chat/messages", content=chunks).status_code == 413


def test_security_headers_and_no_caching_of_api_data():
    client = TestClient(app)
    r = client.post("/api/chat/messages", content=b"{}")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert client.get("/api/me/avatar").headers["cache-control"] == "private, max-age=60"  # an endpoint's own choice stays


def test_production_refuses_example_secrets():
    example = Settings(_env_file=None, environment="production", jwt_secret="change-me", encryption_key="",
                       admin_email="admin@example.com", admin_password="change-me-admin", cookie_secure=False)
    assert {"JWT_SECRET", "INTERNAL_API_KEY", "ENCRYPTION_KEY", "ADMIN_PASSWORD", "COOKIE_SECURE"} <= set(
        example.unsafe_for_production())
    with pytest.raises(RuntimeError):
        example.check_production()
    secret = "x" * 40
    good = Settings(_env_file=None, environment="production", jwt_secret=secret, internal_api_key=secret,
                    mcp_user_token=secret, mcp_market_token=secret, encryption_key="k", admin_email="a@example.com",
                    admin_password="a-long-admin-password", cookie_secure=True)
    assert good.unsafe_for_production() == []
    Settings(_env_file=None, environment="development").check_production()  # never blocks development
