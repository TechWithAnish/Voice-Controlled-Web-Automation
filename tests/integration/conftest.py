"""Fixtures for the opt-in live-browser tests."""

from __future__ import annotations

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Fixture Page</title></head>
<body style="height: 4000px">
  <a href="#target" id="apostrophe">Don't have an account?</a>
  <button type="button" aria-label="Save &quot;draft&quot;">Save</button>
  <a href="#second">Sign in</a>
  <div id="spacer" style="height: 3000px"></div>
  <a href="#bottom" id="bottom-link">Bottom link</a>
  <script>
    document.addEventListener('click', function (event) {
      if (event.target.tagName === 'A' || event.target.tagName === 'BUTTON') {
        document.title = 'clicked:' + (event.target.textContent || '').trim();
      }
    });
  </script>
</body></html>
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def fixture_site(tmp_path_factory) -> str:
    """Serve a local page over HTTP and yield its URL."""
    root: Path = tmp_path_factory.mktemp("site")
    (root / "index.html").write_text(PAGE, encoding="utf-8")

    port = _free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
