"""A bounded speech sequence: acknowledgement, then the current answer."""
from uuid import uuid4
import time
from app.ai.cancellation import CancellationToken


class SpeechQueue:
    def __init__(self):
        self.active = None
        self.pending = None

    def _activate(self, item):
        ttl = {"ack": 8, "progress": 10, "context": 12, "greeting": 10}.get(item["kind"], 25)
        item["token"].deadline = time.monotonic() + ttl
        self.active = item
        return item

    def enqueue(self, text, emotion, *, kind="result", pose=None, page=None):
        item = {"id": uuid4().hex, "text": text, "emotion": emotion, "kind": kind,
                "pose": pose or emotion, "page": page, "token": CancellationToken()}
        if self.active:
            if kind in {"progress", "context", "greeting"}:
                return None  # Background narration never talks over a reply.
            if kind == "result" and self.active["kind"] == "ack":
                if self.pending:
                    self.pending["token"].cancel()
                self.pending = item
                return None
            self.cancel()
        return self._activate(item)

    def finish(self, voice_id):
        if not self.active or self.active["id"] != voice_id:
            return None
        following = self.pending
        self.active = self.pending = None
        return self._activate(following) if following else None

    def cancel(self):
        for item in (self.active, self.pending):
            if item:
                item["token"].cancel()
        self.active = self.pending = None
