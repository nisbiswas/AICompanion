from dataclasses import dataclass


@dataclass
class ConversationMessage:
    role: str
    content: str


class ConversationContext:

    MAX_MESSAGES = 12

    def __init__(self):
        self.messages: list[ConversationMessage] = []

    def add_user_message(self, message: str):
        self.messages.append(
            ConversationMessage(
                role="user",
                content=message,
            )
        )

        self._trim()

    def add_assistant_message(self, message: str):
        self.messages.append(
            ConversationMessage(
                role="assistant",
                content=message,
            )
        )

        self._trim()

    def get_messages(self) -> list[dict]:
        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]

    def clear(self):
        self.messages.clear()

    def _trim(self):
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]
