"""Cancellation shared by HTTP, inference and speech without queued Qt slots."""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Event
import time


class RequestCancelled(BaseException):
    """Deliberately bypass generic tool/error recovery."""


@dataclass
class CancellationToken:
    deadline: float | None = None
    event: Event = field(default_factory=Event)

    def cancel(self):
        self.event.set()

    @property
    def cancelled(self):
        return self.event.is_set() or (self.deadline is not None and time.monotonic() >= self.deadline)

    def check(self):
        if self.cancelled:
            raise RequestCancelled()


CURRENT_TOKEN = ContextVar("request_cancellation", default=None)


def check_cancelled():
    token = CURRENT_TOKEN.get()
    if token:
        token.check()


@contextmanager
def request_scope(token):
    marker = CURRENT_TOKEN.set(token)
    try:
        token.check()
        yield
        token.check()
    finally:
        CURRENT_TOKEN.reset(marker)


def run_async(factory):
    token = CURRENT_TOKEN.get()

    async def run():
        task = asyncio.create_task(factory())
        try:
            while not task.done():
                if token:
                    token.check()
                await asyncio.wait({task}, timeout=0.05)
            if token:
                token.check()
            return task.result()
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    return asyncio.run(run())
