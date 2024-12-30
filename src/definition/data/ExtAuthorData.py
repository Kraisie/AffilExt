from dataclasses import dataclass

from definition.data.Author import Author


@dataclass
class ExtResults:
    scheme_name: str
    authors: list[Author]
    score: float


@dataclass
class ExtAuthorInfo:
    ext_type: str
    extractions: list[ExtResults]
