import json

from .ollama_client import OllamaClient
from .prompts import SYSTEM_PROMPT
from .response import AgentResponse, AgentState, AgentIntent


class CompanionAgent:

    def __init__(self):
        self.llm = OllamaClient()

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def respond(self, user_message: str) -> AgentResponse:

        self.messages.append(
            {
                "role": "user",
                "content": user_message,
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

        return response