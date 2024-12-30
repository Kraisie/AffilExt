import logging
import typing
from pathlib import Path

import unicodedata
from rapidfuzz import process, fuzz, utils

import ror_dl
import threaded_run
import util
from definition.data.Author import Author
from definition.data.ExtAuthorData import ExtResults
from definition.data.MatchedAuthorData import MatchedPaperData, MatchedAffiliationInfo, MatchedAuthorInfo
from definition.data.RorDataset import RorDataset
from extract_author_aff import get_author_matchings_by_name

_TOP_MATCHES_LIMIT = 10

_logger: logging.Logger = logging.getLogger(__name__)


def _get_matched_affiliation_infos(matched_author: dict, ror_orgs_dict: dict) -> list[MatchedAffiliationInfo]:
    aff_matches: list[dict] = matched_author["aff_matches"]
    matched_affiliation_infos = []
    for aff_match in aff_matches:
        ext_name = aff_match["ext_name"]
        ror_id = aff_match["ror_id"]
        ror_org = ror_orgs_dict[ror_id]
        score = aff_match["score"]
        matched_affiliation_infos.append(
            MatchedAffiliationInfo(ext_name, ror_org, score)
        )

    return matched_affiliation_infos


def _get_matched_author_infos(matching_data: dict, ror_orgs_dict: dict) -> list[MatchedAuthorInfo]:
    matched_author_infos = []
    for matched_author in matching_data["matched_authors"]:
        name_match = matched_author["name_match"]
        arxiv_name = name_match["arxiv_name"]
        ext_name = name_match["ext_name"]
        score = name_match["score"]
        matched_affiliation_infos = _get_matched_affiliation_infos(matched_author, ror_orgs_dict)
        matched_author_infos.append(
            MatchedAuthorInfo(arxiv_name, ext_name, score, matched_affiliation_infos)
        )

    return matched_author_infos


def _get_matched_paper_data(matching_data: dict, ror_orgs_dict: dict) -> MatchedPaperData:
    matched_authors = _get_matched_author_infos(matching_data, ror_orgs_dict)
    return MatchedPaperData(matched_authors)


def _resolve_ror_id(matching_data: dict, args: tuple) -> None:
    # matching_data = {
    #   "paper_dir": Path,
    #   "matched_authors": [
    #       {
    #           "name_match": {
    #               "arxiv_name": str,
    #               "ext_name": str,
    #               "score": float
    #           },
    #           "aff_matches": [
    #               {
    #                   "ror_id": str,
    #                   "ext_name": str,
    #                   "score": float
    #               }, ...
    #           ]
    #       }, ...
    #   ]
    # }
    ror_orgs_dict: dict = args[0]
    paper_dir = matching_data.get("paper_dir", None)
    if paper_dir is None:
        return

    matched_paper_data = _get_matched_paper_data(matching_data, ror_orgs_dict)
    if matched_paper_data:
        paper_dir = typing.cast(Path, paper_dir)  # paper_dir is a path and not None (IDE complains otherwise)
        util.write_obj_to_json(paper_dir, util.MATCHED_DATA_FILE, matched_paper_data)


def _process_ror_orgs_to_dict(ror_dataset: RorDataset) -> dict:
    ror_dict = {}
    for ror_org in ror_dataset.data:
        # use the ROR-ID as key and pass the object as value
        ror_dict[ror_org.ror_id] = ror_org

    return ror_dict


def _get_best_match(matches: list[tuple[str, float, int]], affiliation: str) -> tuple[str, float, int]:
    # get the best match using the ratio()-score. We do that as a score of partial_ratio() only scores
    # a substring inside affiliation. When there is a good substring match we want to check the whole
    # affiliation to assure longer strings do not have a disadvantage. E.g. "Techno" would have a
    # partial_ratio() of 100 in any affiliation with "Technology" in their name. To allow a string
    # like "Georgia Institute of Technology" we compare all top partial_ratio() matches with the score
    # they get using ratio()
    best = ("", -1.0, -1)
    for match in matches:
        score = fuzz.ratio(match[0], affiliation)
        if score > best[1]:
            best = (match[0], score, match[2])

    return best


def _match_authors(arxiv_authors: list[Author], ext_authors: list[Author], matched_affiliations: dict) -> list[dict]:
    author_matchings = get_author_matchings_by_name(arxiv_authors, ext_authors, scorer=fuzz.ratio)
    matched_authors = []
    for author_matching in author_matchings:  # author_matching = (score, (arxiv, ext))
        score = author_matching[0]
        arxiv_author = author_matching[1][0]
        ext_author = author_matching[1][1]
        name_match = {
            "arxiv_name": arxiv_author.name,
            "ext_name": ext_author.name,
            "score": score
        }

        affiliation_matches = []
        for affiliation in ext_author.affiliations:
            matched_affiliation = matched_affiliations[affiliation]
            if not matched_affiliation:
                continue

            affiliation_matches.append({
                "ror_id": matched_affiliation["matched_ror_id"],
                "ext_name": affiliation,
                "score": matched_affiliation["score"]
            })

        matched_authors.append({
            "name_match": name_match,
            "aff_matches": affiliation_matches
        })

    return matched_authors


def _run_single_element(paper_dir: Path, args: tuple) -> dict | None:
    if not (arxiv_metadata := util.read_json(paper_dir, util.ARXIV_METADATA_FILE)):
        return None

    if not (ext_aff := util.read_json(paper_dir, util.EXTRACTED_DATA_FILE)):
        return None

    extractions = ext_aff.extractions
    if len(ext_aff.extractions) == 0:
        return None

    if util.file_exists(paper_dir, util.MATCHED_DATA_FILE):
        return None

    matched_affiliations: dict = args[0]  # {"extracted_aff" : {ror_id, score}, ...}
    arxiv_authors = arxiv_metadata.authors
    best_extraction = _get_best_extraction(extractions)
    ext_authors = best_extraction.authors
    matched_authors = _match_authors(arxiv_authors, ext_authors, matched_affiliations)
    return {
        "paper_dir": paper_dir,
        "matched_authors": matched_authors
    }


def _get_matched_affiliation(affiliation: str, args: tuple) -> tuple[str, tuple[str, float]]:
    research_orgs: list[tuple[str, str]] = args[0]
    org_names = [org[1] for org in research_orgs]
    preprocessed_affiliation = _pre_process_string(affiliation)
    # extract the top 10 matches
    matches = process.extract(
        # we use partial ratio as we search for a substring inside the extracted affiliation
        # https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html#rapidfuzz.fuzz.partial_ratio
        # we use no processor as we already pre-process the entries ourselves
        preprocessed_affiliation, org_names, scorer=fuzz.partial_ratio, limit=_TOP_MATCHES_LIMIT
    )

    # best_match = (matched string, score of ratio(), index in research_orgs)
    best_match = _get_best_match(matches, preprocessed_affiliation)
    return affiliation, (research_orgs[best_match[2]][0], best_match[1])


def _match_affiliations(affiliations: set[str], ror_orgs: list[tuple[str, str]]) -> dict:
    matched_affs: list[tuple[str, tuple[str, float]]] = threaded_run.run_with_results(
        affiliations, _get_matched_affiliation, ror_orgs
    )

    # build a dict of matches {"extracted_aff" : {ror_id, score}, ...}
    affs = {}
    for affiliation in matched_affs:
        ext_aff_string = affiliation[0]
        values = affiliation[1]
        affs[ext_aff_string] = {
            "matched_ror_id": values[0],
            "score": values[1]
        }

    return affs


def _get_best_extraction(extractions: list[ExtResults]) -> ExtResults:
    if len(extractions) == 1:
        return extractions[0]

    best = extractions[0]
    for extraction in extractions[1:]:
        if extraction.score > best.score:
            best = extraction

    return best


def _get_paper_affiliations(paper_dir: Path) -> set[str]:
    affs = set()
    ext_affs = util.read_json(paper_dir, util.EXTRACTED_DATA_FILE)
    if ext_affs and not util.file_exists(paper_dir, util.MATCHED_DATA_FILE):
        ext = _get_best_extraction(ext_affs.extractions)
        for author in ext.authors:
            for affiliation in author.affiliations:
                affs.add(affiliation)

    return affs


def _get_extracted_affiliations(paper_dirs: list[Path]) -> set[str]:
    # get a list of sets and then combine them as managing a multithreaded set is annoying and slow
    affiliation_sets: list[set[str]] = threaded_run.run_with_results(paper_dirs, _get_paper_affiliations)
    unique_affiliations = set()
    for affiliation_set in affiliation_sets:
        for affiliation in affiliation_set:
            unique_affiliations.add(affiliation)

    return unique_affiliations


def _pre_process_string(string: str) -> str:
    # pre-process the name for rapidfuzz matching
    normalized_unicode = unicodedata.normalize('NFD', string)
    return utils.default_process(normalized_unicode)


def _process_ror_orgs(ror_dataset: RorDataset) -> list[tuple[str, str]]:
    ror_orgs = []
    for ror_org in ror_dataset.data:
        ror_id = ror_org.ror_id
        for name in ror_org.names:
            processed_name = _pre_process_string(name)
            if len(processed_name) > 0:  # ignore full unicode names (like cyrillic names)
                ror_orgs.append((ror_id, processed_name))

    return ror_orgs


def _get_ror_dataset() -> RorDataset:
    if not util.file_exists(util.get_ror_dir(), util.ROR_DATASET_FILE):
        _logger.warning("Did not find ROR dataset file! Downloading it now.")
        ror_dl.prepare_dataset()

    return util.read_json(util.get_ror_dir(), util.ROR_DATASET_FILE)


def run(paper_dirs: list[Path]) -> None:
    """
    Match the extracted author metadata to author names listed on arXiv and a curated list of research
    organizations (ROR dataset).
    """
    util.configure_logger(_logger)
    _logger.info("Preparing ROR dataset for Matching.")
    ror_dataset = _get_ror_dataset()
    ror_orgs = _process_ror_orgs(ror_dataset)
    _logger.info("Matching extracted data. This might take a while!")
    extracted_affiliations = _get_extracted_affiliations(paper_dirs)
    matched_affiliations = _match_affiliations(extracted_affiliations, ror_orgs)
    matched_data = threaded_run.run_with_results(paper_dirs, _run_single_element, matched_affiliations)
    _logger.info("Preparing ROR dataset for assignments.")
    ror_orgs_dict = _process_ror_orgs_to_dict(ror_dataset)
    _logger.info("Assigning ROR Organizations to extracted data.")
    threaded_run.run(matched_data, _resolve_ror_id, ror_orgs_dict)
