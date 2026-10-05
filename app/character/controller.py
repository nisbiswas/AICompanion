from app.ai.agent import CompanionAgent
from app.ai.response import AgentResponse


class CharacterController:
    def __init__(self):
        self.agent = CompanionAgent()

    def respond_to_user(self, message: str) -> AgentResponse:
        message = message.strip()

        if not message:
            return None

        return self.agent.respond(message)