import httpx


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string"
        },
        "voice_line": {
            "type": "string"
        },
        "read_aloud": {
            "type": "boolean"
        },
        "state": {
            "type": "string",
            "enum": [
                "IDLE",
                "THINKING",
                "TALKING",
                "CONFUSED",
                "WORKING",
                "WAITING_FOR_PERMISSION"
            ]
        },
        "intent": {
            "type": "string",
            "enum": [
                "CONVERSATION",
                "CLARIFICATION",
                "CODE_ANALYSIS",
                "CODE_CHANGE",
                "GENERAL_QUESTION",
                "IMAGE_GENERATION"
            ]
        },
        "permission_required": {
            "type": "boolean"
        },
        "emotion": {
            "type": "string",
            "enum": [
                "NEUTRAL",
                "HAPPY",
                "SHY",
                "ANNOYED",
                "SAD",
                "CURIOUS",
                "SURPRISED",
                "THINKING"
            ]
        },
        "tool_request": {
            "type": ["object", "null"]
        }
    },
    "required": [
        "response",
        "voice_line",
        "read_aloud",
        "state",
        "intent",
        "permission_required",
        "emotion",
        "tool_request"
    ]
}


class OllamaClient:

    def __init__(
        self,
        model: str = "qwen2.5:14b",
        base_url: str = "http://127.0.0.1:11434",
    ):
        self.model = model
        self.base_url = base_url

    def unload(self):
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "keep_alive": 0, "stream": False},
            timeout=120.0,
        )
        response.raise_for_status()

    def chat(self, messages: list[dict], schema: dict | None = None) -> str:

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema if schema is not None else RESPONSE_SCHEMA,
        }

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]
