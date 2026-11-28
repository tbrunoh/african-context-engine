"""Release 2.4.2: HTTP visitors reach HTTPS with no port in the address. No network."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from ace_engine.app import create_app
from ace_engine.server import AceApp, https_location

ROOT = Path(__file__).resolve().parents[1]
HOST = "ace.korext.com"


def call(app, method, path, query="", headers=None):
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "CONTENT_LENGTH": "0",
           "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "http"}
    env.update(headers or {})
    out = {}
    payload = b"".join(app(env, lambda s, h: out.update(status=s, headers=h)))
    return int(out["status"].split()[0]), dict(out["headers"]), payload


HTTP = {"HTTP_X_ACE_SCHEME": "http"}


@pytest.fixture()
def site(engine):
    return AceApp(engine, public=True, https_host=HOST)


def test_http_goes_to_the_same_page_on_https_with_no_port(site):
    code, h, body = call(site, "GET", "/try", "x=1", HTTP)
    assert code == 301 and h["Location"] == f"https://{HOST}/try?x=1" and body == b""
    assert ":443" not in h["Location"]
    code, h, _ = call(site, "HEAD", "/", "", HTTP)
    assert code == 301 and h["Location"] == f"https://{HOST}/"


def test_a_post_keeps_its_method(site):
    code, h, _ = call(site, "POST", "/mcp", "", HTTP)
    assert code == 308 and h["Location"] == f"https://{HOST}/mcp"


def test_the_host_is_always_the_configured_one(site):
    code, h, _ = call(site, "GET", "//evil.example/x", "", {**HTTP, "HTTP_HOST": "evil.example"})
    assert code == 301 and h["Location"].startswith(f"https://{HOST}/")
    assert h["Location"] == f"https://{HOST}//evil.example/x"


def test_paths_and_queries_are_escaped():
    env = {**HTTP, "PATH_INFO": "/a b/é".encode().decode("latin-1"), "QUERY_STRING": "q=a b\r\nX: y"}
    location = https_location(env, HOST)
    assert location == f"https://{HOST}/a%20b/%C3%A9?q=a%20b%0D%0AX:%20y"
    assert "\r" not in location and "\n" not in location and " " not in location


def test_https_and_unmarked_requests_are_served(site, engine):
    code, _, body = call(site, "GET", "/try")
    assert code == 200 and body
    code, _, _ = call(site, "GET", "/try", "", {"HTTP_X_ACE_SCHEME": "https"})
    assert code == 200
    code, _, _ = call(AceApp(engine, public=True), "GET", "/try", "", HTTP)
    assert code == 200  # no host configured, no redirect: a local server is never sent elsewhere


def test_a_paused_demo_still_redirects(engine):
    code, h, _ = call(AceApp(engine, public=True, paused=True, https_host=HOST), "GET", "/", "", HTTP)
    assert code == 301 and h["Location"] == f"https://{HOST}/"


def test_a_bad_host_refuses_to_start(engine):
    for bad in ("https://ace.korext.com", "ace.korext.com/x", "ace.korext.com:443", "evil@ace.korext.com", "localhost"):
        with pytest.raises(ValueError):
            AceApp(engine, https_host=bad)


def test_create_app_reads_the_host(engine):
    app = create_app({"ACE_PUBLIC": "1", "ACE_HTTPS_HOST": HOST}, engine=engine, start_threads=False)
    assert call(app, "GET", "/healthz", "", HTTP)[0] == 301
    assert call(create_app({}, engine=engine, start_threads=False), "GET", "/healthz", "", HTTP)[0] == 200


def test_the_load_balancer_marks_http_and_strips_the_mark_on_https():
    setup = (ROOT / "deploy" / "gcp" / "setup.sh").read_text()
    http = setup[setup.index("name: ace-redirect"):setup.index("YAML", setup.index("name: ace-redirect"))]
    assert "backendServices/ace-web-backend" in http and "headerName: x-ace-scheme" in http
    assert "headerValue: http" in http and "replace: true" in http and "UrlRedirect" not in http
    https = setup[setup.index("name: ace-urlmap"):setup.index("YAML", setup.index("name: ace-urlmap"))]
    assert https.count("requestHeadersToRemove: [x-ace-scheme]") == 2
    assert "ACE_HTTPS_HOST=${DOMAIN}" in setup
    smoke = (ROOT / "deploy" / "gcp" / "smoke.py").read_text()
    assert 'f"https://{host}/try?x=1"' in smoke and '"X-Ace-Scheme": "http"' in smoke
