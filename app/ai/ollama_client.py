import httpx


class OllamaClient:

    def __init__(
        self,
        model: str = "qwen2.5:14b",
        base_url: str = "http://127.0.0.1:11434",
    ):
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict]) -> str:

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]