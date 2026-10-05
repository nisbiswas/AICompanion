def __init__(self):

    self.llm = OllamaClient()

    self.memory = Memory()

    self.messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]