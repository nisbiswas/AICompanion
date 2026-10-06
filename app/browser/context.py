from dataclasses import dataclass
from datetime import datetime


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
    ):
        self.browser = browser
        self.title = title
        self.url = url
        self.updated_at = datetime.now().isoformat()

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