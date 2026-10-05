import json

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
from app.ai.context import ConversationContext


class CompanionAgent:

    def __init__(self):

        self.llm = OllamaClient()

        self.memory = Memory()
        self.memory_extractor = MemoryExtractor()

        self.tools = ToolRegistry(PROJECT_ROOT)

        self.context = ConversationContext()

    def _build_memory_context(self) -> str:

        facts = self.memory.get_facts()

        if not facts:
            return "No stored memories."

        return "\n".join(
            f"- {fact}"
            for fact in facts
        )

    def _build_messages(self) -> list[dict]:

        memory_context = self._build_memory_context()

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "system",
                "content": (
                    "Known memories about the user:\n"
                    f"{memory_context}"
                ),
            },
        ]

        messages.extend(
            self.context.get_messages()
        )

        return messages

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

    def _parse_response(self, raw_response: str) -> AgentResponse:
        try:
            data = json.loads(raw_response)

            response_text = str(
                data.get("response", "")
            ).strip()

            voice_line = str(
                data.get("voice_line", "")
            ).strip()

            # If the model doesn't provide a voice line,
            # create a short spoken version from the response.
            #
            # This keeps the voice pipeline working even if
            # the local model occasionally omits the optional
            # voice field.
            if not voice_line:
                print("WARNING: Qwen did not provide a voice_line.")

            return AgentResponse(
                response=response_text,

                state=AgentState(
                    data.get(
                    "state",
                    "TALKING",
                 )
                ),

                intent=AgentIntent(
                    data.get(
                    "intent",
                    "CONVERSATION",
                    )
                ),

                permission_required=bool(
                data.get(
                    "permission_required",
                    False,
                )
            ),

                voice_line=voice_line,

                read_aloud=bool(
                    data.get(
                        "read_aloud",
                        False,
                    )
                ),

                tool_request=data.get(
                "tool_request"
                ),

                emotion=AgentEmotion(
                    data.get(
                    "emotion",
                    "NEUTRAL",
                    )
                ),
            )

        except (
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ) as error:

            print(
            "========== RESPONSE PARSE ERROR =========="
            )
            print(
            "RAW RESPONSE:"
            )
            print(raw_response)
            print(
                "ERROR:",
                error,
            )
            print(
                "==========================================="
            )

            return AgentResponse(
                response=(
                    "I had trouble understanding "
                    "my own response."
                ),

                state=AgentState.CONFUSED,

                intent=AgentIntent.CLARIFICATION,

                permission_required=False,

                voice_line=(
                    "Hmm... something went wrong "
                    "while I was thinking."
                ),

                read_aloud=False,

                tool_request=None,

                emotion=AgentEmotion.NEUTRAL,
            )

    def respond(
        self,
        user_message: str,
    ) -> AgentResponse:

        user_message = user_message.strip()

        if not user_message:
            return None

        self.context.add_user_message(
            user_message
        )

        max_tool_calls = 3

        response = None

        for _ in range(max_tool_calls):

            messages = self._build_messages()

            raw_response = self.llm.chat(
                messages
            )

            response = self._parse_response(
                raw_response
            )

            self.context.add_assistant_message(
                raw_response
            )

            if not response.tool_request:
                break

            try:

                tool_result = self._execute_tool(
                    response.tool_request
                )

            except Exception as error:

                tool_result = (
                    f"Error executing tool: {error}"
                )

            self.context.add_user_message(
                (
                    "TOOL RESULT\n"
                    f"Tool: "
                    f"{response.tool_request.get('tool')}\n"
                    f"Result:\n"
                    f"{tool_result}\n\n"
                    "Use this tool result to answer the "
                    "original user request. "
                    "If more information is needed, "
                    "you may request another available "
                    "read-only tool."
                )
            )

        fact = self.memory_extractor.extract(
            user_message
        )

        if fact:

            self.memory.add_fact(
                fact
            )

            print(
                f"Memory updated with new fact: {fact}"
            )

        return response