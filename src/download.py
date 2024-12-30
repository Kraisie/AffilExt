import logging
import re
import tarfile
from datetime import datetime
from pathlib import Path

import bs4
import jsonpickle

import util
from ArxivAPI import ArxivAPI
from definition.data.ArxivMetadata import ArxivMetadata
from definition.data.Author import Author

_SRC_FILE_NAME = "psrcdl.tar.gz"
_logger: logging.Logger = logging.getLogger(__name__)

# own filter to sanitize names in tar for windows usage
# also applies the "data" filter of tarfile
def _tar_filter_sanitize(member: tarfile.TarInfo, path: str | Path, /) -> tarfile.TarInfo | None:
    if isinstance(path, Path):
        path = str(path)

    invalid_chars_win = r"[:*?\"|<>]"
    if re.search(invalid_chars_win, member.name):
        member = member.replace(name=re.sub(invalid_chars_win, "_", path))

    return tarfile.data_filter(member, path)


def _process_single_member(tar, tar_member_name: str, arxiv_id: str) -> bool:
    if tar_member_name.endswith(".pdf") or tar_member_name.endswith(".html") or tar_member_name.endswith(".ps"):
        file_ext = tar_member_name.split(".")[-1]
        _logger.warning("Extraction failed! tar only contains a %s file!", file_ext)
        return False

    # file named like the arxiv id without file extension containing the TeX source (new id)
    # file named like the numeric part of the id (old id -> cs/9810022 -> 9810022)
    if tar_member_name != arxiv_id and tar_member_name != re.sub("[^0-9]", "", arxiv_id):
        return False

    paper_tex_dir = util.get_paper_tex_dir_by_arxiv_id(arxiv_id)
    tar.extract(tar_member_name, path=paper_tex_dir, filter="data")  # see _process_tar_members for info
    if not util.rename_file(paper_tex_dir, tar_member_name, "main.tex"):
        _logger.warning("Could not rename '%s' to a .tex-file!", tar_member_name)
        return False

    return True


def _process_tar_members(tar: tarfile.TarFile, arxiv_id: str) -> bool:
    tar_member_names = tar.getnames()
    if len(tar_member_names) == 1:
        return _process_single_member(tar, tar_member_names[0], arxiv_id)
    else:
        tar_members = tar.getmembers()
        tex_files = [tar_member for tar_member in tar_members if tar_member.name.endswith(".tex")]
        if len(tex_files) == 0:
            _logger.warning("Failed! tar-file does not contain any .tex-files.")
            return False

        # using the filter to prevent some security issues. "data" will become the default in python 3.14
        # https://docs.python.org/3/library/tarfile.html#tarfile.TarFile.extractall
        # https://docs.python.org/3/library/tarfile.html#tarfile-extraction-filter
        # extract(all) also does not handle invalid characters on windows.
        # manually sanitize the names before extraction with own filter implementation:
        # https://github.com/python/cpython/issues/80715#issuecomment-1533155463
        for tex_file in tex_files:
            try:
                tar.extract(tex_file, path=util.get_paper_tex_dir_by_arxiv_id(arxiv_id), filter=_tar_filter_sanitize)
            except OSError:
                _logger.warning("Can not extract file! Invalid name of tar member: '%s'", tex_file.name)
                continue

        return True


# working with tar commands would work (even for windows due to WSL), but the syntax for those commands is different.
# Windows: tar -xzf <name> "*.tex"
# Linux: tar -xzf <name> --wildcard --no-anchored "*.tex"
# Adding more commands to check the file contents would further increase the issue and would require platform dependent
# methods. That's why instead of using tar commands via subprocess, the tarfile lib gets used here.
def _extract_tar(tar_file_path: Path, arxiv_id: str) -> bool:
    _logger.info("Extracting tar file.")
    if not tarfile.is_tarfile(tar_file_path):
        _logger.warning("Extraction failed! '%s' is not a tar-file.", tar_file_path.name)
        return False

    with tarfile.open(tar_file_path, "r") as tar:
        success = _process_tar_members(tar, arxiv_id)

    util.delete_file(tar_file_path)
    return success


def _download_src_tar(arxiv_api: ArxivAPI, arxiv_id, paper_dir) -> Path:
    _logger.info("Requesting src tar from arxiv.")
    response = arxiv_api.get_src(arxiv_id)
    src_file = response.content
    return util.write_to_file(paper_dir, _SRC_FILE_NAME, src_file, flags="wb", encoding=None)  # no encoding needed


def download_paper(arxiv_api: ArxivAPI, arxiv_id: str) -> bool:
    paper_dir = util.get_paper_dir(arxiv_id)
    tar_file_path = _download_src_tar(arxiv_api, arxiv_id, paper_dir)
    return _extract_tar(tar_file_path, arxiv_id)


def _run(arxiv_api: ArxivAPI, paper_metadata: ArxivMetadata, to_skip: set[str]) -> None:
    arxiv_id = paper_metadata.arxiv_id
    _logger.info("Downloading arXiv paper '%s'...", arxiv_id)
    paper_dir = util.get_paper_dir(arxiv_id)
    if not util.file_exists(paper_dir, util.ARXIV_METADATA_FILE):
        util.write_obj_to_json(paper_dir, util.ARXIV_METADATA_FILE, paper_metadata)

    if arxiv_id in to_skip:
        _logger.info("'%s' in skip list! Skipping download.", arxiv_id)
        return

    if len(util.get_all_files_recursive(util.get_paper_tex_dir_by_arxiv_id(arxiv_id), extension=".tex")) > 0:
        _logger.info("TeX files found on disk for '%s'! Skipping download.", arxiv_id)
        return

    if not download_paper(arxiv_api, arxiv_id):
        _logger.warning("Download failed! Adding '%s' to skip list.", arxiv_id)
        to_skip.add(arxiv_id)


def _replace_month_abbr(date_str: str) -> str:
    months = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }
    # "%d %b %Y %H:%M:%S %Z"
    parts = date_str.split(" ")
    parts[1] = months[parts[1]]
    return " ".join(parts)

def _get_kaggle_version_data(metadata: dict) -> tuple[str, str]:
    paper_versions = metadata.get("versions", [{"version": "v1", "created": metadata.get("update_date", "")}])
    paper_version = paper_versions[-1].get("version", "")  # get the latest version
    published_on = paper_versions[0].get("created", "")  # get the original release date
    # DATETIME IS LOCALE DEPENDENT!!! DATETIME DOES NOT SUPPORT USING OTHER LOCALES!!!
    # We could set the locale with locale.setlocale but that is platform dependent and discouraged.
    # Instead, we drop the day name abbreviation and transform the month name abbreviation to a number.
    # We need to replace the month name abbreviation because the day of month is not zero-padded so the month isn't
    # always at the same position.
    # transform "%a, %d %b %Y %H:%M:%S %Z" ("Mon, 2 Apr 2007 19:18:42 GMT")
    # to        "%d %m %Y %H:%M:%S %Z"     ("2 04 2007 19:18:42 GMT")
    # to        "%Y-%m-%dT%H:%M:%SZ"       ("2007-04-02T19:18:42Z") -> ArXiv format
    published_on = _replace_month_abbr(published_on[5:])  # remove "Mon, " and the month abbr
    dt = datetime.strptime(published_on, "%d %m %Y %H:%M:%S %Z")
    published_on = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return paper_version, published_on


def _get_kaggle_author_list(metadata: dict) -> list[Author]:
    author_list = metadata.get("authors_parsed", [])
    authors = []
    for author in author_list:
        # "The list for each author will have at least three elements for
        # keyname, firstname(s) and suffix. The keyname will always have content
        # but the other strings might be empty strings if there is no firstname
        # or suffix. Any additional elements after the first three are affiliations,
        # there may be zero or more."
        # -> https://github.com/mattbierbaum/arxiv-public-datasets/blob/master/arxiv_public_data/authors.py#L66
        keyname = author[0].strip()
        given_name = author[1].strip() if len(author) > 1 else ""
        suffix = author[2].strip() if len(author) > 2 else ""  # like Jr., Sr. or roman numbers
        affiliations = []
        for affiliation in author[3:]:
            affiliations.append(affiliation)

        name = " ".join([given_name, keyname, suffix])
        authors.append(Author(name, affiliations))

    return authors


def _get_kaggle_metadata(line: str) -> ArxivMetadata:
    metadata = jsonpickle.decode(line)
    arxiv_id = metadata["id"]
    title = metadata.get("title", "")
    comment = metadata.get("comments", "")
    journal_ref = metadata.get("journal-ref", "")
    doi = metadata.get("doi", "")
    categories = metadata.get("categories", "").split(" ")  # the arXiv dataset already filters any non-arXiv categories

    # format: "%Y-%m-%d" (kaggle) -> %Y-%m-%dT%H:%M:%SZ" (arXiv)
    last_updated = metadata.get("update_date", "")
    if last_updated:
        last_updated += "T11:11:11Z"  # set some time to adhere to arxiv format

    version, published_on = _get_kaggle_version_data(metadata)
    authors = _get_kaggle_author_list(metadata)
    return ArxivMetadata(
        arxiv_id, version, title, comment, journal_ref, doi, categories, last_updated, published_on, authors
    )


def run_kaggle(arxiv_api: ArxivAPI, kaggle_path: Path, arxiv_category: str) -> None:
    """
    Download LaTeX files from arXiv using the data provided in the Kaggle dataset of arXiv metadata.
    """
    util.configure_logger(_logger)
    to_skip = set(util.read_json(util.get_papers_dir(), util.SKIPPED_DL_FILE) or [])
    try:
        with open(kaggle_path, "r") as f:
            # each line is a JSON object, 'jsonlines' format
            for line in f:
                paper_metadata = _get_kaggle_metadata(line)
                if arxiv_category not in paper_metadata.categories:
                    # skip any papers that are not of the requested category
                    continue

                _run(arxiv_api, paper_metadata, to_skip)
    finally:
        # save the skipped downloads even on KeyboardInterrupt or other exceptions
        util.write_obj_to_json(util.get_papers_dir(), util.SKIPPED_DL_FILE, to_skip)


def _get_author_list(entry: bs4.element.Tag) -> list[Author]:
    authors = []
    for author_tag in entry.findAll("author"):
        if not author_tag.name:
            continue

        # .name does not work here as that is used by the lib for the tag name
        name = str(author_tag.find("name").string).strip()
        affiliations = []
        for affiliation_tag in author_tag.findAll("arxiv:affiliation"):
            affiliations.append(str(affiliation_tag.string))

        authors.append(Author(name, affiliations))

    return authors


def _get_arxiv_id(arxiv_abs_url: str) -> tuple[str, str]:
    version_index = arxiv_abs_url.rfind("v")
    paper_version = arxiv_abs_url[version_index:] if version_index != -1 else "v1"
    arxiv_id = arxiv_abs_url[:version_index].replace("http://arxiv.org/abs/", "")
    return arxiv_id, paper_version


def _str_contains_digit_char(string: str) -> bool:
    for char in string:
        if char.isdigit():
            return True

    return False


def _get_categories(entry: bs4.Tag) -> list[str]:
    category_tags = entry.findAll("category")
    if len(category_tags) == 0:
        primary_category = entry.find("arxiv:primary_category")
        if primary_category:
            return [str(primary_category["term"])]
        else:
            return []

    # categories can be a classification from arXiv, ACM or MSC. multiple arXiv categories are normally in
    # multiple category tags, while multiple ACM/MSC categories are separated by a semicolon. These category names
    # also often include multiple dots and digits which arXiv does not.
    # https://arxiv.org/category_taxonomy
    categories = []
    for category_tag in category_tags:
        category_content = str(category_tag["term"])

        # ignore category lists from ACM/MSC
        if ";" in category_content:
            continue

        # ignore categories that do not contain exactly one dot
        if category_content.count(".") != 1:
            continue

        # if ignore categories with digits
        if _str_contains_digit_char(category_content):
            continue

        categories.append(category_content)

    return categories


def _get_optional_tag(entry: bs4.Tag, tag_name: str, ):
    tag = entry.find(tag_name)
    if not tag:
        return ""

    return str(tag.string)


def _get_paper_metadata(entry: bs4.element.Tag) -> ArxivMetadata:
    # use str() to convert bs4.NavigableString to built-in str as otherwise JSON encoding will fail
    arxiv_abs_url = str(entry.id.string)
    arxiv_id, version = _get_arxiv_id(arxiv_abs_url)
    title = str(entry.title.string)
    comment = _get_optional_tag(entry, "arxiv:comment")
    journal_ref = _get_optional_tag(entry, "arxiv:journal_ref")
    doi = _get_optional_tag(entry, "arxiv:doi")
    categories = _get_categories(entry)
    last_updated = str(entry.updated.string)  # format: "%Y-%m-%dT%H:%M:%SZ"
    published_on = str(entry.published.string)  # format: "%Y-%m-%dT%H:%M:%SZ"
    authors = _get_author_list(entry)
    return ArxivMetadata(
        arxiv_id, version, title, comment, journal_ref, doi, categories, last_updated, published_on, authors
    )


def run_api(arxiv_api: ArxivAPI, entries: list[bs4.Tag]) -> None:
    """
    Download LaTeX files from arXiv using its API to get a list of papers.
    """
    util.configure_logger(_logger)
    to_skip = set(util.read_json(util.get_papers_dir(), util.SKIPPED_DL_FILE) or [])
    try:
        for entry in entries:
            paper_metadata = _get_paper_metadata(entry)
            _run(arxiv_api, paper_metadata, to_skip)
    finally:
        # save the skipped downloads even on KeyboardInterrupt or other exceptions
        util.write_obj_to_json(util.get_papers_dir(), util.SKIPPED_DL_FILE, to_skip)
