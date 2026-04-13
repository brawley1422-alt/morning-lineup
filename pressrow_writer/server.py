"""Stdlib HTTP server with custom routing for Press Row Writer's Room.

Single-threaded on purpose: single user, local-only, no concurrency concerns.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from pressrow_writer import routes


HOST = "127.0.0.1"
PORT = 8787


class WriterRoomHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quieter logging — only errors and important events
        if args and len(args) > 1 and isinstance(args[1], str):
            code = args[1]
            if code.startswith("4") or code.startswith("5"):
                super().log_message(format, *args)

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # ─── Route dispatch ──────────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/":
            status, ct, body = routes.serve_index()
            return self._send(status, ct, body)

        # Silently swallow favicon/manifest requests — these are browser auto-requests
        if path in ("/favicon.ico", "/manifest.json"):
            return self._send(204, "text/plain", b"")

        if path.startswith("/static/"):
            status, ct, body = routes.serve_static(path[len("/static/"):])
            return self._send(status, ct, body)

        # API GET routes
        if path == "/api/progress":
            status, ct, body = routes.api_progress()
            return self._send(status, ct, body)

        if path == "/api/writers":
            status, ct, body = routes.api_writers()
            return self._send(status, ct, body)

        if path == "/api/teams":
            status, ct, body = routes.api_teams()
            return self._send(status, ct, body)

        if path == "/api/llm/status":
            status, ct, body = routes.api_llm_status()
            return self._send(status, ct, body)

        if path == "/api/swipe/next":
            status, ct, body = routes.api_swipe_next()
            return self._send(status, ct, body)

        if path == "/api/card/ghost":
            status, ct, body = routes.api_card_ghost()
            return self._send(status, ct, body)

        self._send(404, "text/plain", b"not found")

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/chat/message":
            status, ct, resp = routes.api_chat_message(body)
            return self._send(status, ct, resp)

        if path.startswith("/api/chat/commit/"):
            task_type = path[len("/api/chat/commit/"):]
            status, ct, resp = routes.api_chat_commit(task_type, body)
            return self._send(status, ct, resp)

        if path == "/api/swipe/accept":
            status, ct, resp = routes.api_swipe_accept(body)
            return self._send(status, ct, resp)

        if path == "/api/swipe/reject":
            status, ct, resp = routes.api_swipe_reject(body)
            return self._send(status, ct, resp)

        if path == "/api/swipe/anchor":
            status, ct, resp = routes.api_swipe_anchor(body)
            return self._send(status, ct, resp)

        if path == "/api/card/ghost/commit":
            status, ct, resp = routes.api_card_ghost_commit(body)
            return self._send(status, ct, resp)

        if path == "/api/card/ghost/oracle":
            status, ct, resp = routes.api_card_ghost_oracle(body)
            return self._send(status, ct, resp)

        self._send(404, "text/plain", b"not found")


def serve():
    """Start the server. Blocks until Ctrl+C."""
    httpd = HTTPServer((HOST, PORT), WriterRoomHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"Press Row Writer's Room running at {url}")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
