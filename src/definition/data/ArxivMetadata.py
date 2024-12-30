from dataclasses import dataclass

from definition.data.Author import Author


@dataclass
class ArxivMetadata:
    arxiv_id: str
    version: str
    title: str
    comment: str
    journal_ref: str
    doi: str
    categories: list[str]
    last_updated: str  # format: "%Y-%m-%dT%H:%M:%SZ"
    published_on: str  # format: "%Y-%m-%dT%H:%M:%SZ"
    authors: list[Author]
