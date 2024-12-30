from dataclasses import dataclass


@dataclass
class LatexCmd:
    original_cmd: str
    sanitized_cmd: str


@dataclass
class ExtCmdData:
    documentclasses: list[str]
    cmds: list[LatexCmd]
