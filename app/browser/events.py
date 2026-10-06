from dataclasses import dataclass
from enum import Enum


class BrowserEventType(str, Enum):
    CONTEXT_CHANGED = "CONTEXT_CHANGED"


@dataclass
class BrowserEvent:
    event_type: BrowserEventType
    browser: str
    title: str
    url: str
    previous_title: str = ""
    previous_url: str = ""

    def as_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "browser": self.browser,
            "title": self.title,
            "url": self.url,
            "previous_title": self.previous_title,
            "previous_url": self.previous_url,
        }