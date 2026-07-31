from __future__ import annotations

import json
import logging
from time import perf_counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

logger = logging.getLogger(__name__)


def create_server(host: str, port: int, service):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            started_at = perf_counter()
            parsed = urlparse(self.path)
            payload = service.handle(
                parsed.path.strip("/"),
                {key: value for key, value in parse_qsl(parsed.query, keep_blank_values=True)},
            )
            status_code = 200
            if payload.get("error") == "not_found":
                status_code = 404
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            logger.info(
                "feed_adapter_http method=GET path=%s query=%s status=%s client=%s elapsed_ms=%.2f",
                parsed.path,
                parsed.query or "-",
                status_code,
                self.client_address[0] if self.client_address else "-",
                (perf_counter() - started_at) * 1000,
            )

        def log_message(self, format: str, *args) -> None:
            return None

    return ThreadingHTTPServer((host, port), Handler)
