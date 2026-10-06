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

                    page_text = str(
                        data.get("page_text", "")
                        )

                    event = context.update(
                        browser=str(data.get("browser", "")),
                        title=str(data.get("title", "")),
                        url=str(data.get("url", "")),
                        page_text=page_text,
                    )

                    print(
                        "PAGE TEXT:",
                        page_text[:500].replace("\n"," ")
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