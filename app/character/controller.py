from app.ai.agent import CompanionAgent
from app.ai.response import AgentResponse
from app.permissions.manager import PermissionManager


class CharacterController:

    def __init__(
        self,
        permissions: PermissionManager | None = None,
    ):
        self.agent = CompanionAgent(
            permissions=permissions
        )

    def respond_to_user(
        self,
        message: str,
    ) -> AgentResponse:

        message = message.strip()

        if not message:
            return None

        return self.agent.respond(message)

    def set_browser_context(
        self,
        browser_context: dict,
    ):

        self.agent.set_browser_context(
            browser_context
        )