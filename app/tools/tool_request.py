from dataclasses import dataclass


@dataclass
class ToolRequest:
    tool: str
    arguments: dict

    