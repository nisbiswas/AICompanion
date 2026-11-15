import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from PySide6.QtCore import QObject, Signal

from app.browser.context import BrowserContext
from app.permissions.manager import Permission, PermissionManager


class BrowserBridge(QObject):
    event_received = Signal(object)

    HOST = "127.0.0.1"
    PORT = 8766

    def __init__(
        self,
        context: BrowserContext,
        permissions: PermissionManager,
    ):
        super().__init__()

        self.context = context
        self.permissions = permissions

        self.server = None
        self.thread = None

    def start(self):
        context = self.context
        permissions = self.permissions
        bridge = self

        class Handler(BaseHTTPRequestHandler):

            def do_POST(self):
                if self.path != "/context":
                    self.send_response(404)
                    self.end_headers()
                    return

                if not permissions.is_allowed(
                    Permission.BROWSER_CONTEXT
                ):
                    self.send_response(403)
                    self.end_headers()
                    return

                try:
                    length = int(
                        self.headers.get("Content-Length", 0)
                    )

                    body = self.rfile.read(length)

                    data = json.loads(
                        body.decode("utf-8")
                    )
                    previous_capture = (context.capture_info or {}).get("captured_at")
                    incoming_capture = data.get("captured_at")
                    if previous_capture and incoming_capture and incoming_capture < previous_capture:
                        self.send_response(204)
                        self.end_headers()
                        return

                    page_text = ""
                    if permissions.is_allowed(Permission.BROWSER_PAGE_READ):
                        page_text = str(data.get("page_text", ""))[:24000]
                    can_read = permissions.is_allowed(Permission.BROWSER_PAGE_READ)

                    event = context.update(
                        browser=str(data.get("browser", "")),
                        title=str(data.get("title", "")),
                        url=str(data.get("url", "")),
                        page_text=page_text,
                        code_text=str(data.get("code_text", ""))[:16000] if can_read else "",
                        selected_text=str(data.get("selected_text", ""))[:4000] if can_read else "",
                        capture_info={key: data.get(key) for key in ("captured_at", "truncated", "text_length", "code_length", "capture_error")},
                    )

                    print(
                        "BROWSER CAPTURE:", len(page_text), "text characters;",
                        len(context.code_text), "code characters; truncated:", bool(data.get("truncated"))
                    )

                    if event:
                        bridge.event_received.emit(event)

                    self.send_response(200)
                    self.end_headers()

                    self.wfile.write(
                        b'{"ok":true}'
                    )

                except Exception as exc:
                    print(
                        f"Browser bridge error: {exc}"
                    )

                    self.send_response(400)
                    self.end_headers()

            def log_message(self, format, *args):
                return

        self.server = HTTPServer(
            (self.HOST, self.PORT),
            Handler,
        )

        self.thread = Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

        self.thread.start()

        print(
            f"Browser bridge listening on "
            f"http://{self.HOST}:{self.PORT}"
        )

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.thread = None
