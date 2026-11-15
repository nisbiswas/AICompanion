"""Search outcomes are application state, never something the LLM invents."""
from dataclasses import dataclass, field
from enum import Enum


class SearchStatus(str, Enum):
    SUCCESS = "success"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    EMPTY = "empty"


@dataclass
class SearchOutcome:
    status: SearchStatus
    query: str
    results: list[dict] = field(default_factory=list)
    detail: str = ""

    @property
    def message(self):
        if self.status == SearchStatus.DISABLED:
            return ("Research is OFF (WEB_SEARCH permission is not granted). "
                    "Turn on Research in the chat input, then ask again so I can verify the current answer.")
        if self.status == SearchStatus.EMPTY:
            return ("The web search completed but returned no usable results. "
                    "I haven't verified the current answer. Try a more specific search or check SearXNG's search engines.")
        return (f"Web search is unavailable: {self.detail} "
                "I haven't verified the current answer, so I won't substitute an old recommendation.")

    def evidence(self):
        return "\n\n".join(
            f"{i}. {item['title']}\nURL: {item['url']}\nSummary: {item['content']}"
            for i, item in enumerate(self.results, 1)
        )

    def source_links(self):
        return "\n".join(f"- [{item['title'] or 'Source'}]({item['url']})" for item in self.results[:5])
