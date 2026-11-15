"""One running request and one replaceable pending request. Latest submission wins."""
from dataclasses import dataclass
from uuid import uuid4
from app.ai.cancellation import CancellationToken


@dataclass
class WorkItem:
    kind: str
    text: str
    browser: dict
    token: CancellationToken
    id: str


class RequestScheduler:
    def __init__(self):
        self.active = None
        self.pending = None

    def submit(self, kind, text, browser):
        item = WorkItem(kind, text, dict(browser), CancellationToken(), uuid4().hex)
        if self.pending:
            self.pending.token.cancel()
        if self.active:
            self.active.token.cancel()
            self.pending = item
            return None
        self.active = item
        return item

    def accepts(self, request_id):
        return bool(self.active and self.active.id == request_id and not self.active.token.cancelled)

    def finish(self, request_id):
        if not self.active or self.active.id != request_id:
            return None
        self.active = self.pending
        self.pending = None
        return self.active

    def cancel(self):
        if self.active:
            self.active.token.cancel()
        if self.pending:
            self.pending.token.cancel()
        self.pending = None
