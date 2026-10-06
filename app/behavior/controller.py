import time

from app.browser.events import BrowserEvent


class BehaviorController:

    def __init__(self):
        self.last_event = None
        self.last_reaction_time = 0.0

        self.reaction_cooldown = 30.0

    def handle_browser_event(
        self,
        event: BrowserEvent,
    ) -> str | None:

        if not self.should_react(event):
            return None

        now = time.monotonic()

        if (
            now - self.last_reaction_time
            < self.reaction_cooldown
        ):
            return None

        self.last_event = event
        self.last_reaction_time = now

        return self.build_reaction(event)

    def should_react(
        self,
        event: BrowserEvent,
    ) -> bool:

        url = event.url.lower()
        title = event.title.lower()

        if not url and not title:
            return False

        if url.startswith("chrome://"):
            return False

        if url.startswith("edge://"):
            return False

        if url.startswith("about:"):
            return False

        if "new tab" in title:
            return False

        return True

    def build_reaction(
        self,
        event: BrowserEvent,
    ) -> str:

        if event.previous_title:
            return (
                f"You switched to {event.title}."
            )

        return (
            f"You're looking at {event.title}."
        )