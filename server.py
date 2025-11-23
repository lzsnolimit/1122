import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple

try:
    from service import db_service
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"Failed to import database service: {e}")


HOST: str = "127.0.0.1"
PORT: int = 8000


def cors_headers() -> Tuple[str, str, str]:
    """Return common CORS headers for development use."""
    return (
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, OPTIONS"),
        ("Access-Control-Allow-Headers", "*"),
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "AdviceServer/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        logging.info("%s - - %s", self.address_string(), format % args)

    def _write_headers(self, status: int = 200, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        for k, v in cors_headers():
            self.send_header(k, v)
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        # Respond to CORS preflight
        self._write_headers(status=204, content_type="text/plain")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/get_last_10_advises":
            self._handle_get_last_10_advises()
            return

        self._write_headers(status=404)
        body = json.dumps({"error": "not_found", "message": "unknown path"}, ensure_ascii=False)
        self.wfile.write(body.encode("utf-8"))

    def _handle_get_last_10_advises(self) -> None:
        try:
            items = db_service.get_last_10_advises()
            body = json.dumps(items, ensure_ascii=False)
            self._write_headers(status=200)
            self.wfile.write(body.encode("utf-8"))
        except Exception as e:
            logging.exception("Failed to fetch advises: %s", e)
            self._write_headers(status=500)
            body = json.dumps({"error": "internal_error", "message": "unexpected database error"}, ensure_ascii=False)
            self.wfile.write(body.encode("utf-8"))


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    logging.info("Server running at http://%s:%d", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        logging.info("Shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
