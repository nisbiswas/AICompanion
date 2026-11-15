import os
import json
import httpx
from .cancellation import run_async, check_cancelled


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
        self.model = os.getenv("OLLAMA_MODEL", model)
        self.base_url = os.getenv("OLLAMA_BASE_URL", base_url)
        self.context_length = int(os.getenv("OLLAMA_NUM_CTX", "24576"))

    def unload(self):
        async def send():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/api/generate",
                    json={"model": self.model, "keep_alive": 0, "stream": False})
                response.raise_for_status()
        run_async(send)

    def chat(self, messages: list[dict], schema: dict | None = None) -> str:

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "format": schema if schema is not None else RESPONSE_SCHEMA,
            "options": {"num_ctx": self.context_length, "num_predict": 4096,
                        "temperature": 0.2 if schema is not None else 0.7},
        }

        async def generate():
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                # Retry a token-limited JSON response with a larger output budget.
                for budget in (4096, 8192):
                    payload["options"]["num_predict"] = budget
                    parts, final = [], None
                    async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            check_cancelled()
                            if not line.strip():
                                continue
                            event = json.loads(line)
                            if event.get("error"):
                                raise RuntimeError(event["error"])
                            parts.append(event.get("message", {}).get("content", ""))
                            if event.get("done"):
                                final = event
                    if final is None:
                        raise RuntimeError("The model connection ended before the answer was complete. Please retry.")
                    if final.get("done_reason") == "length":
                        continue
                    result = "".join(parts)
                    json.loads(result)  # Never present partial structured output as a complete answer.
                    return result
                raise RuntimeError("The answer exceeded the output limit. Ask for a smaller section; no partial answer was saved.")

        return run_async(generate)
