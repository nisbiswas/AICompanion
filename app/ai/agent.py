import json

from app.tools import tool_request

from .ollama_client import OllamaClient
from .prompts import SYSTEM_PROMPT
from .response import (
    AgentResponse,
    AgentState,
    AgentIntent,
    AgentEmotion,
)
from app.memory.memory import Memory
from app.memory.memory_extractor import MemoryExtractor
from app.config import PROJECT_ROOT
from app.tools.registry import ToolRegistry


class CompanionAgent:

    def __init__(self):

        self.llm = OllamaClient()

        self.memory = Memory()
        self.memory_extractor = MemoryExtractor()
        self.tools = ToolRegistry(PROJECT_ROOT)
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

    def _execute_tool(self, tool_request: dict) -> str:

        tool_name = tool_request.get("tool")
        arguments = tool_request.get("arguments", {})

        if tool_name == "list_directory":

            path = arguments.get("path", ".")

            result = self.tools.list_directory(path)

            return "\n".join(result)

        if tool_name == "read_file":

            path = arguments.get("path")

            if not path:
                return "Error: read_file requires a path."

            return self.tools.read_file(path)

        return f"Unknown tool: {tool_name}"

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


        max_tool_calls=3

        for _ in range(max_tool_calls):
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
                            tool_request=data.get("tool_request"),
                            emotion=AgentEmotion(data.get("emotion", "NEUTRAL"))
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
                        tool_request=None,
                        emotion=AgentEmotion.NEUTRAL,
)
                return response

            self.messages.append(
                {
                    "role": "assistant",
                    "content": raw_response,
                }
            )

            if not response.tool_request:
                break

            try:
                tool_result = self._execute_tool(response.tool_request)
            except Exception as error:
                tool_result = (
                    f"Error executing tool: {error}"
                )

            self.messages.append(
                {
                    "role": "user",
                     "content": (
                    "TOOL RESULT\n"
                    f"Tool: {response.tool_request.get('tool')}\n"
                    f"Result:\n{tool_result}\n\n"
                    "Use this tool result to answer the original "
                    "user request. If more information is needed, "
                    "you may request another available read-only tool."
                ),
                }
            )

        fact = self.memory_extractor.extract(user_message)

        if fact:
            self.memory.add_fact(fact)
            print(f"Memory updated with new fact: {fact}")

        return response