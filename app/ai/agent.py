import json

from .ollama_client import OllamaClient
from .prompts import SYSTEM_PROMPT
from .response import AgentResponse, AgentState, AgentIntent
from memory.memory import Memory
from memory.memory_extractor import MemoryExtractor


class CompanionAgent:

    def __init__(self):

        self.llm = OllamaClient()

        self.memory = Memory()
        self.memory_extractor = MemoryExtractor()

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def _build_memory_context(self) -> str:

        facts = self.memory.get_facts()

        if not facts:
            return "No stored memories."

        return "\n".join(
            f"- {fact}"
            for fact in facts
        )

    def respond(self, user_message: str) -> AgentResponse:

        self.messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        memory_context = self._build_memory_context()

        self.messages.append(
            {
                "role": "system",
                "content": (
                    "Known memories about the user:\n"
                    f"{memory_context}"
                ),
            }
        )

        raw_response = self.llm.chat(self.messages)

        try:
            data = json.loads(raw_response)

            response = AgentResponse(
                response=data["response"],
                state=AgentState(data["state"]),
                intent=AgentIntent(data["intent"]),
                permission_required=bool(
                    data["permission_required"]
                ),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as error:

            response = AgentResponse(
                response=(
                    "I had trouble understanding my own response. "
                    f"Internal error: {error}"
                ),
                state=AgentState.CONFUSED,
                intent=AgentIntent.CLARIFICATION,
                permission_required=False,
            )

        self.messages.append(
            {
                "role": "assistant",
                "content": raw_response,
            }
        )

        fact = self.memory_extractor.extract(user_message)

        if fact:
            self.memory.add_fact(fact)
            print(f"[Memory] Stored: {fact}")

        return response