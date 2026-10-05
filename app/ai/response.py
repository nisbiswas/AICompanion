from dataclasses import dataclass
from enum import Enum


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
    tool_request: dict | None = None
    emotion: AgentEmotion = AgentEmotion.NEUTRAL