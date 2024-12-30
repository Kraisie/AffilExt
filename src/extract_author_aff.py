import logging
from pathlib import Path

from rapidfuzz import utils, process
from rapidfuzz.distance import Indel

import threaded_run
import util
from definition.data.ArxivMetadata import ArxivMetadata
from definition.data.Author import Author
from definition.data.ExtAuthorData import ExtAuthorInfo, ExtResults
from definition.data.ExtCmdData import ExtCmdData, LatexCmd
from definition.data.MultiCmdScheme import MultiCmdScheme
from definition.data.SingleCmdScheme import SingleCmdScheme
# noinspection PyUnresolvedReferences
from definition.multi_cmd_scheme import *
# noinspection PyUnresolvedReferences
from definition.single_cmd_scheme import *  # import all schemes, the comment above prevents PyCharm from removing this
from definition.single_cmd_scheme import cmd_util

_logger: logging.Logger = logging.getLogger(__name__)


def _build_wrapped_single_command(ext_cmds: ExtCmdData) -> ExtCmdData:
    cmd_str = " ".join([cmd.sanitized_cmd for cmd in ext_cmds.cmds])
    original_cmd = "Wrapped Multiple Commands as one"
    wrapped_cmd = fr"\author{{{cmd_str}}}"
    latex_cmd = LatexCmd(original_cmd, wrapped_cmd)
    return ExtCmdData(ext_cmds.documentclasses, [latex_cmd])


def _identify_valid_multi_cmd_schemes(cmds: list[str]) -> list[MultiCmdScheme]:
    valid_schemes = []
    for scheme in MultiCmdScheme.__subclasses__():
        scheme_obj = scheme()
        if scheme_obj.validate(cmds):
            valid_schemes.append(scheme_obj)

    return valid_schemes


def _multi_cmd_ext(ext_cmds: ExtCmdData, arxiv_metadata: ArxivMetadata) -> tuple[str, list[ExtResults]]:
    cmds = [cmd.sanitized_cmd for cmd in ext_cmds.cmds]
    valid_schemes = _identify_valid_multi_cmd_schemes(cmds)
    if len(valid_schemes) == 0:
        _logger.debug("There are no valid extraction schemes for the cmds of '%s'.", arxiv_metadata.arxiv_id)
        cmd = _build_wrapped_single_command(ext_cmds)
        return "wrapped_multi", _single_cmd_ext(cmd, arxiv_metadata)

    author_affs = []
    arxiv_authors = arxiv_metadata.authors
    for scheme in valid_schemes:
        author_aff = scheme.extract(cmds)
        if not author_aff:
            continue

        score = _score_ext_data(arxiv_authors, author_aff)
        author_affs.append(ExtResults(scheme.__class__.__name__, author_aff, score))

    return "multi", author_affs


def _weighted_arithmetic_mean(scores_and_weights: list[tuple[float, float]]) -> float:
    # the importance of these scores is not equal, e.g. missing authors are way more problematic than slight
    # differences in the name format. Missing affiliations are not great, but to be expected.
    scores = [x[0] for x in scores_and_weights]
    weights = [x[1] for x in scores_and_weights]
    weighted_score_sum = sum([score * weight for score, weight in zip(scores, weights)])
    return weighted_score_sum / sum(weights)


def _match_unequal_cardinality(
        arxiv_authors: list[Author], ext_authors: list[Author], scorer=Indel.normalized_similarity
) -> list[tuple[float, tuple[Author, Author]]]:
    most_similar = []
    for arxiv_author in arxiv_authors:
        score, authors = _match_name(arxiv_author, ext_authors, scorer)  # authors = (arxiv, ext)
        most_similar.append((score, authors))

    return most_similar


def _match_name(
        arxiv_author: Author, ext_authors: list[Author], scorer=Indel.normalized_similarity
) -> tuple[float, tuple[Author, Author]]:
    author_name = arxiv_author.name
    ext_author_names = [a.name for a in ext_authors]

    # Calculates the normalized indel (INsertion-DELetion) similarity. The indel distance calculates the
    # minimum number of insertions and deletions required to change one sequence into the other. The resulting
    # score ranges from 0.0 to 1.0
    # -> https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Indel.html#rapidfuzz.distance.Indel.normalized_similarity
    # the default processor pre-processes the strings by:
    # - removing all non-alphanumeric characters
    # - trimming whitespaces
    # - converting all characters to lower case
    # -> https://rapidfuzz.github.io/RapidFuzz/Usage/utils.html
    # that is useful in regard to remaining latex elements and Unicode characters.
    _, score, index = process.extractOne(author_name, ext_author_names, scorer=scorer, processor=utils.default_process)

    best_match = ext_authors[index]
    return score, (arxiv_author, best_match)


def _match_equal_cardinality(
        arxiv_authors: list[Author], ext_authors: list[Author], scorer=Indel.normalized_similarity
) -> list[tuple[float, tuple[Author, Author]]]:
    unmatched_authors = ext_authors.copy()  # create a copy of the list so we can modify it
    most_similar = []
    for arxiv_author in arxiv_authors:
        score, authors = _match_name(arxiv_author, unmatched_authors, scorer)  # authors = (arxiv, ext)

        most_similar.append((score, authors))
        unmatched_authors.remove(authors[1])  # avoid matching this author again for another name

    return most_similar


def get_author_matchings_by_name(
        arxiv_authors: list[Author], ext_authors: list[Author], scorer=Indel.normalized_similarity
) -> list[tuple[float, tuple[Author, Author]]]:
    # if the number of arxiv authors and extracted authors are the same we can remove the matched name for
    # further matches. However, if they are not of the same length we need to assume that there is wrong data
    # on at least one of the author lists. we then match all names against each other.
    if len(arxiv_authors) == len(ext_authors):
        return _match_equal_cardinality(arxiv_authors, ext_authors, scorer)
    else:
        return _match_unequal_cardinality(arxiv_authors, ext_authors, scorer)


def _score_author_name_similarity(arxiv_authors: list[Author], ext_authors: list[Author]) -> float:
    best_name_matches = get_author_matchings_by_name(arxiv_authors, ext_authors)
    return sum(ms[0] for ms in best_name_matches) / len(best_name_matches)  # value between 0 and 1


def _score_author_ratio(len_arxiv: int, len_ext: int) -> float:
    # if we extract more authors than there are authors on arXiv, we can assume that we have some false data,
    # thus, we need to adjust the calculation for that possibility, as we do not want a better score for more
    # extracted authors than there are authors.
    # however, extracting 6 authors when there are 5 is better than extracting 8 authors when there are 5
    if len_arxiv == 0:
        return 0.0

    if len_ext <= len_arxiv:
        return len_ext / len_arxiv
    elif len_ext >= len_arxiv * 2:
        return 0.0
    else:
        return abs(len_ext - 2 * len_arxiv) / len_arxiv


def _score_ext_data(arxiv_authors: list[Author], ext_authors: list[Author]) -> float:
    extracted_author_ratio = _score_author_ratio(len(arxiv_authors), len(ext_authors))
    author_name_similarity = _score_author_name_similarity(arxiv_authors, ext_authors)
    author_with_aff_ratio = len([a for a in ext_authors if len(a.affiliations) > 0]) / len(ext_authors)
    scores_and_weights = [
        (extracted_author_ratio, 0.5),
        (author_name_similarity, 0.2),
        (author_with_aff_ratio, 0.3)
    ]
    return _weighted_arithmetic_mean(scores_and_weights)


def _identify_valid_single_cmd_schemes(cmd_name: str, cmd_content: str) -> list[SingleCmdScheme]:
    valid_schemes = []
    for scheme in SingleCmdScheme.__subclasses__():
        scheme_obj = scheme()
        if scheme_obj.validate(cmd_name, cmd_content):
            valid_schemes.append(scheme_obj)

    return valid_schemes


def _single_cmd_ext(ext_cmds: ExtCmdData, arxiv_metadata: ArxivMetadata) -> list[ExtResults]:
    cmd = ext_cmds.cmds[0].sanitized_cmd
    cmd_name = cmd_util.get_cmd_name(cmd).lower()
    cmd_content = cmd_util.get_cmd_content(cmd)
    if not cmd_name or not cmd_content:
        _logger.warning("Could not identify cmd name or cmd content in '%s'", cmd)
        return []

    valid_schemes = _identify_valid_single_cmd_schemes(cmd_name, cmd_content)
    if len(valid_schemes) == 0:
        _logger.debug(
            "There are no valid extraction schemes for the single cmd of '%s': %s",
            arxiv_metadata.arxiv_id, cmd
        )

    author_affs = []
    arxiv_authors = arxiv_metadata.authors
    for scheme in valid_schemes:
        author_aff = scheme.extract(cmd_name, cmd_content)
        if not author_aff:
            continue

        score = _score_ext_data(arxiv_authors, author_aff)
        author_affs.append(ExtResults(scheme.__class__.__name__, author_aff, score))

    return author_affs


def _run_single_element(paper_dir: Path) -> None:
    util.configure_logger(_logger)
    if not (arxiv_metadata := util.read_json(paper_dir, util.ARXIV_METADATA_FILE)):
        _logger.error("Could not read arXiv metadata for '%s'. Skipping extraction", paper_dir.name)
        return

    if util.file_exists(paper_dir, util.EXTRACTED_DATA_FILE):
        _logger.debug("Extracted data file already exists for '%s'. Skipping extraction.", paper_dir.name)
        return

    if not (ext_cmds := util.read_json(paper_dir, util.CMDS_FILE)) or len(ext_cmds.cmds) == 0:
        _logger.debug("'%s' does not have any extracted commands! Skipping extraction.", paper_dir.name)
        return

    if len(ext_cmds.cmds) == 1:
        ext_type = "single"
        ext_results = _single_cmd_ext(ext_cmds, arxiv_metadata)
    else:
        ext_type, ext_results = _multi_cmd_ext(ext_cmds, arxiv_metadata)

    _logger.debug(
        "Performed %s extractions for '%s'. Scores: %s", len(ext_results), paper_dir.name,
        sorted([res.score for res in ext_results], key=float, reverse=True)  # best to worst
    )

    if ext_results:
        ext_data = ExtAuthorInfo(ext_type, ext_results)
        util.write_obj_to_json(paper_dir, util.EXTRACTED_DATA_FILE, ext_data)


def run(paper_dirs: list[Path]) -> None:
    """
    Extract metadata related to the authors from the LaTeX commands we extracted before.
    We are looking for the name and the affiliations of the authors.
    """
    threaded_run.run(paper_dirs, _run_single_element)
