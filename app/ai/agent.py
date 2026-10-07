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
from app.permissions.manager import PermissionManager, Permission


class CompanionAgent:

    def __init__(
            self,
            permissions: PermissionManager | None = None,
    ):

        self.llm = OllamaClient()

        self.memory = Memory()
        self.memory_extractor = MemoryExtractor()

        self.tools = ToolRegistry(PROJECT_ROOT)

        self.context = ConversationContext()

        self.browser_context = {}

        self.context = ConversationContext()

        self.browser_context = {}

        self.permissions=permissions or PermissionManager()

    def set_browser_context(self, browser_context: dict):
        self.browser_context = dict(browser_context)

    def _build_browser_context(self) -> str:

        if not self.browser_context:
            return (
                "No browser context is currently available."
            )

        return (
            "Current browser context:\n"
            f"Browser: {self.browser_context.get('browser', '')}\n"
            f"Page title: {self.browser_context.get('title', '')}\n"
            f"URL: {self.browser_context.get('url', '')}\n\n"
            "This is browser metadata only. "
            "You can see the browser, page title, and URL, "
            "but you cannot see page contents, images, videos, "
            "comments, or other page data unless the user grants "
            "page-read permission."
        )

    def _build_memory_context(self) -> str:

        facts = self.memory.get_facts()

        if not facts:
            return "No stored memories."

        return "\n".join(
            f"- {fact}"
            for fact in facts
        )

    def _build_browser_context(self) -> str:

        if not self.browser_context:
            return (
                "No browser context is currently available."
            )

        browser = self.browser_context.get(
            "browser",
            "",
        )

        title = self.browser_context.get(
            "title",
            "",
        )

        url = self.browser_context.get(
            "url",
            "",
        )

        page_text = self.browser_context.get(
            "page_text",
            "",
            )
        if not browser and not title and not url:
            return (
                "No browser context is currently available."
            )

        if page_text:
            return (
                "Current browser context:\n"
                f"Browser: {browser}\n"
                f"Page title: {title}\n"
                f"Page text: {page_text}\n"
                f"URL: {url}\n\n"
                "Browser access is READ-ONLY. "
                "You may use the visible page text to answer "
                "the user's questions. "
                "You cannot click, type, navigate, submit forms, "
                "or otherwise interact with the browser."
            )
        return (
            "Current browser context:\n"
            f"Browser: {browser}\n"
            f"Page title: {title}\n"
            f"URL: {url}\n\n"
            "No visible page text is currently available."
        )

    def _build_messages(self) -> list[dict]:

        memory_context = self._build_memory_context()
        browser_context = self._build_browser_context()

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
            {
                "role": "system",
                "content": browser_context,
            },
            {
                "role": "system",
                "content": self._build_browser_context(),
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

        if tool_name == "web_search":

            print(f"TOOL REQUEST: web_search -> {arguments}")

            if not self.permissions.is_allowed(
                Permission.WEB_SEARCH
            ):
                return (
                    "WEB_SEARCH permission is not granted. "
                    "You cannot search the internet."
                )

            query = arguments.get("query", "").strip()

            if not query:
                return (
                    "Error: web_search requires a query."
                )

            limit = arguments.get("limit", 5)

            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = 5

            limit = max(1, min(limit, 10))

            results = self.tools.search_web(
                query,
                limit,
            )

            if not results:
                return "No search results found."

            lines = []

            for index, result in enumerate(
                results,
                start=1,
            ):
                lines.append(
                    f"{index}. {result['title']}\n"
                    f"URL: {result['url']}\n"
                    f"Summary: {result['content']}"
                )

            return "\n\n".join(lines)

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

            if not voice_line:
                print(
                    "WARNING: Qwen did not provide a voice_line."
                )

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
            print("RAW RESPONSE:")
            print(raw_response)
            print("ERROR:", error)
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

        # -------------------------------------------------
        # PERSIST USER MESSAGE
        # -------------------------------------------------

        self.context.add_user_message(
            user_message
        )

        # -------------------------------------------------
        # TEMPORARY REQUEST CONTEXT
        # -------------------------------------------------

        messages = self._build_messages()

        max_tool_calls = 3

        response = None

        for _ in range(max_tool_calls):

            raw_response = self.llm.chat(
                messages
            )

            response = self._parse_response(
                raw_response
            )

            # -------------------------------------------------
            # NO TOOL -> FINAL RESPONSE
            # -------------------------------------------------

            if not response.tool_request:

                self.context.add_assistant_message(
                    raw_response
                )

                break

            # -------------------------------------------------
            # TOOL REQUEST
            # -------------------------------------------------

            tool_name = response.tool_request.get(
                "tool"
            )

            try:

                tool_result = self._execute_tool(
                    response.tool_request
                )

            except Exception as error:

                tool_result = (
                    f"Error executing tool: {error}"
                )

            # -------------------------------------------------
            # TEMPORARY TOOL CONTEXT
            # -------------------------------------------------

            messages.append(
                {
                    "role": "assistant",
                    "content": raw_response,
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "TOOL RESULT\n"
                        f"Tool: "
                        f"{tool_name}\n"
                        f"Result:\n"
                        f"{tool_result}\n\n"
                        "Use this tool result to answer the "
                        "original user request. "
                        "If more information is needed, "
                        "you may request another available "
                        "read-only tool."
                    ),
                }
            )

        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------

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