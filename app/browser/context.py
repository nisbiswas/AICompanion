from dataclasses import dataclass
from datetime import datetime

from app.browser.events import BrowserEvent, BrowserEventType


@dataclass
class BrowserContext:
    browser: str = ""
    title: str = ""
    url: str = ""
    updated_at: str = ""

    def update(
        self,
        browser: str,
        title: str,
        url: str,
    ) -> BrowserEvent | None:

        previous_browser = self.browser
        previous_title = self.title
        previous_url = self.url

        changed = (
            browser != self.browser
            or title != self.title
            or url != self.url
        )

        if not changed:
            return None

        self.browser = browser
        self.title = title
        self.url = url
        self.updated_at = datetime.now().isoformat()

        return BrowserEvent(
            event_type=BrowserEventType.CONTEXT_CHANGED,
            browser=browser,
            title=title,
            url=url,
            previous_title=previous_title,
            previous_url=previous_url,
        )

    def clear(self):
        self.browser = ""
        self.title = ""
        self.url = ""
        self.updated_at = ""

    def is_available(self) -> bool:
        return bool(self.title or self.url)

    def as_dict(self) -> dict:
        return {
            "browser": self.browser,
            "title": self.title,
            "url": self.url,
            "updated_at": self.updated_at,
        }