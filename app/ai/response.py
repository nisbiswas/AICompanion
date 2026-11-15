from dataclasses import dataclass
from enum import Enum
import re
import unicodedata


def has_readable_text(value) -> bool:
    if not isinstance(value, str):
        return False
    # A list marker such as '-' produces an empty Markdown bullet. HTML-only
    # output can be similarly invisible. Emoji-only replies remain valid.
    visible = re.sub(r"<[^>]*>", "", value)
    return any(char.isalnum() or unicodedata.category(char) == "So" for char in visible)


def readable_reply(text, voice_line="", *, allow_empty=False) -> str:
    for candidate in (text, voice_line):
        if has_readable_text(candidate):
            return candidate.strip()
    return "" if allow_empty else "I didn't produce a readable reply. Please try again."


class AgentState(str, Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    TALKING = "TALKING"
    CONFUSED = "CONFUSED"
    WORKING = "WORKING"
    WAITING_FOR_PERMISSION = "WAITING_FOR_PERMISSION"


class AgentIntent(str, Enum):
    CONVERSATION = "CONVERSATION"
    CLARIFICATION = "CLARIFICATION"
    CODE_ANALYSIS = "CODE_ANALYSIS"
    CODE_CHANGE = "CODE_CHANGE"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    IMAGE_GENERATION = "IMAGE_GENERATION"


class AgentEmotion(str, Enum):
    NEUTRAL = "NEUTRAL"
    HAPPY = "HAPPY"
    SHY = "SHY"
    ANNOYED = "ANNOYED"
    SAD = "SAD"
    CURIOUS = "CURIOUS"
    SURPRISED = "SURPRISED"
    THINKING = "THINKING"


@dataclass
class AgentResponse:
    response: str
    state: AgentState
    intent: AgentIntent
    permission_required: bool

    voice_line: str = ""
    read_aloud: bool = False

    tool_request: dict | None = None
    emotion: AgentEmotion = AgentEmotion.NEUTRAL
    image_path: str | None = None
