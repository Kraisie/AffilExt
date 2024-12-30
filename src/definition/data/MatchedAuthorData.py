from dataclasses import dataclass

from definition.data.RorDataset import ResearchOrganization


@dataclass
class MatchedAffiliationInfo:
    ext_name: str
    matched_ror: ResearchOrganization
    score: float


@dataclass
class MatchedAuthorInfo:
    arxiv_name: str
    ext_name: str
    score: float
    affiliations: list[MatchedAffiliationInfo]


@dataclass
class MatchedPaperData:
    matched_authors: list[MatchedAuthorInfo]
