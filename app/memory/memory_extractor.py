import json

from app.ai.ollama_client import OllamaClient


MEMORY_PROMPT = """
You are a memory extraction system.

Your job is to examine the user's latest message and determine whether
it contains information worth remembering across future conversations.

Store only useful, reasonably stable facts.

Good examples:
- The user is building a Kafka broker in Python.
- The user uses Windows.
- The user prefers Python for this project.
- The user's favorite flower is lavender.
- The user's favorite dessert is pistachio ice cream.
- The user enjoys Sekiro and gentle, quiet conversation.
- The user is working on an AI desktop companion.

Explicit preferences, favorite things, names and ongoing goals are useful stable
facts even when unrelated to programming. Preserve them without inventing details.

Do NOT store:
- greetings
- casual conversation
- temporary emotions
- questions
- obvious statements
- information that is only relevant to the current message

Return ONLY valid JSON.

If there is nothing worth remembering:

{
    "remember": false,
    "fact": ""
}

If there is something worth remembering:

{
    "remember": true,
    "fact": "The user is building a Kafka broker in Python."
}
"""


class MemoryExtractor:

    def __init__(self):

        self.llm = OllamaClient()

    def extract(self, user_message: str) -> str | None:

        messages = [
            {
                "role": "system",
                "content": MEMORY_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        raw_response = self.llm.chat(messages, schema={
            "type": "object",
            "properties": {"remember": {"type": "boolean"}, "fact": {"type": "string"}},
            "required": ["remember", "fact"],
            "additionalProperties": False,
        })

        try:
            data = json.loads(raw_response)

        except json.JSONDecodeError:
            return None

        if not data.get("remember", False):
            return None

        fact = data.get("fact", "").strip()

        if not fact:
            return None

        return fact
