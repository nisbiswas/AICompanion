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
    page_text: str = ""
    previous_title: str = ""
    previous_url: str = ""
    code_text: str = ""
    selected_text: str = ""

    def as_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "browser": self.browser,
            "title": self.title,
            "url": self.url,
            "page_text": self.page_text,
            "previous_title": self.previous_title,
            "previous_url": self.previous_url,
            "code_text": self.code_text,
            "selected_text": self.selected_text,
        }

