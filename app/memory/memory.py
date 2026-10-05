import json
from pathlib import Path


class Memory:

    def __init__(self, memory_file: str = "data/memory/facts.json"):

        self.memory_file = Path(memory_file)

        self.memory_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.memory_file.exists():
            self._save({
                "facts": []
            })

    def _load(self) -> dict:

        with self.memory_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    def _save(self, data: dict):

        with self.memory_file.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    def add_fact(self, fact: str):

        data = self._load()

        if fact not in data["facts"]:
            data["facts"].append(fact)

        self._save(data)

    def get_facts(self) -> list[str]:

        data = self._load()

        return data.get("facts", [])