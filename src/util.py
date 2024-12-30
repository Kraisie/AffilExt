import logging
import sys
import typing
from pathlib import Path

import jsonpickle

_logger = logging.getLogger(__name__)
_LOGGER_HANDLER_NAME = "formatted_stdout_handler"  # used to identify our handlers

ARXIV_ENCODING = "utf-8"  # according to docs arxiv feed will always be utf-8 encoded
LOG_LEVEL = logging.INFO

# FILES
ARXIV_METADATA_FILE = "arxiv_metadata.json"
SKIPPED_DL_FILE = "skipped_papers.json"
CMDS_FILE = "cmds.json"
EXTRACTED_DATA_FILE = "extracted_data.json"
ROR_DATASET_FILE = "ror.json"
MATCHED_DATA_FILE = "matched_data.json"
BASIC_STATS_FILE = "basic_stats.json"
STATS_ALL_DATA = "combined_data.json"
FORCE_GRAPH_DATASET_INST = "fg_inst.json"
FORCE_GRAPH_DATASET_COUNTRY = "fg_country.json"

# DIRECTORIES
_DATA_DIR = "data"
_ARXIV_DIR = "arxiv"
_STATS_DIR = "stats"
_REQUESTS_DIR = "requests"
_PAPERS_DIR = "papers"
_PAPER_TEX_DIR = "tex"
_ROR_DIR = "ror"

######### PATHS ###########
# root                    #
# ├─ src                  #
# └─ data                 #
#    ├─ arxiv             #
#    │  ├─ papers         #
#    │  └─ requests       #
#    ├─ ror               #
#    └─ stats             #
###########################
_ROOT_PATH = Path(__file__).parent.parent
_DATA_PATH = _ROOT_PATH / _DATA_DIR
_ARXIV_PATH = _DATA_PATH / _ARXIV_DIR
_PAPERS_PATH = _ARXIV_PATH / _PAPERS_DIR
_REQUESTS_PATH = _ARXIV_PATH / _REQUESTS_DIR
_ROR_PATH = _DATA_PATH / _ROR_DIR
_STATS_PATH = _DATA_PATH / _STATS_DIR

# CREATE PATHS IF NEEDED
Path.mkdir(_PAPERS_PATH, parents=True, exist_ok=True)  # also creates data and arxiv dir
Path.mkdir(_REQUESTS_PATH, parents=True, exist_ok=True)
Path.mkdir(_ROR_PATH, parents=True, exist_ok=True)
Path.mkdir(_STATS_PATH, parents=True, exist_ok=True)


def get_requests_dir() -> Path:
    return _REQUESTS_PATH


def get_papers_dir() -> Path:
    return _PAPERS_PATH


def get_ror_dir() -> Path:
    return _ROR_PATH


def get_stats_dir() -> Path:
    return _STATS_PATH


def get_paper_dirs() -> list[Path]:
    return [paper_dir for paper_dir in _PAPERS_PATH.iterdir() if paper_dir.is_dir()]


def get_paper_dir(arxiv_id: str) -> Path:
    paper_dir = _PAPERS_PATH / sanitize_arxiv_id(arxiv_id)
    if not paper_dir.exists():
        Path.mkdir(paper_dir)

    return paper_dir


def get_paper_tex_dir_by_arxiv_id(arxiv_id: str) -> Path:
    paper_dir = get_paper_dir(arxiv_id)
    return get_paper_tex_dir_by_path(paper_dir)


def get_paper_tex_dir_by_path(paper_dir: Path) -> Path:
    paper_tex_dir = paper_dir / _PAPER_TEX_DIR
    if not paper_tex_dir.exists():
        Path.mkdir(paper_tex_dir)

    return paper_tex_dir


def get_single_cmd_scheme_dir() -> Path:
    util_py_file = Path(__file__)
    code_dir = util_py_file.parent
    return code_dir / "definition" / "single_cmd_scheme"


def get_all_files_recursive(dir_path: Path, extension="") -> list[Path]:
    if not dir_path.is_dir():
        return []

    return [file_path for file_path in list(dir_path.rglob(f"*{extension}")) if
            file_path.is_file()]  # rglob returns a Generator object, list turns it into list of paths


def _should_ignore_file(file_path: Path, ignore_cls: bool) -> bool:
    if not file_path.is_file():
        return True

    if ignore_cls:
        return file_path.name.endswith(".cls.tex")

    return False


def get_all_tex_files(dir_path: Path, ignore_cls=True) -> list[Path]:
    if not dir_path.is_dir():
        return []

    return [file_path for file_path in list(dir_path.rglob(f"*.tex")) if
            not _should_ignore_file(file_path, ignore_cls=ignore_cls)]


# / is not allowed in a directory name on windows and linux
# handle old and new IDs: https://info.arxiv.org/help/arxiv_identifier_for_services.html
# http://arxiv.org/abs/2409.08279v1         new (version is optional; latest if not specified)
# http://arxiv.org/abs/hep-ph/0209124v1     old (version is optional; latest if not specified)
def sanitize_arxiv_id(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_")


def read(file_path: Path, flags="r", encoding=ARXIV_ENCODING) -> str:
    if file_path.is_file():
        try:
            with open(file_path, flags, encoding=encoding, errors="ignore") as file:
                return file.read()
        except OSError:
            # windows defender complains about 2406.04027 05_evaluation.tex as it includes (deobfuscated) malicious src
            _logger.warning("Could not read file '%s'", file_path)
            return ""
    else:
        return ""


def read_file(dir_path: Path, file_name: str) -> str:
    file_path = dir_path / file_name
    return read(file_path)


def dir_exists(base_path: Path, dir_name: str) -> bool:
    dir_path = base_path / dir_name
    return dir_path.is_dir()


def file_exists(dir_path: Path, file_name: str) -> bool:
    file_path = dir_path / file_name
    return file_path.is_file()


def write_to_file(dir_path: Path, file_name: str, file_content: str, flags="w", encoding=ARXIV_ENCODING) -> Path:
    file_path = dir_path / file_name
    with open(file_path, flags, encoding=encoding) as file:
        file.write(file_content)

    return file_path


def write_obj_to_json(dir_path: Path, file_name: str, obj: typing.Any,
                      flags="w", encoding=ARXIV_ENCODING, unpicklable=True, make_refs=False) -> None:
    json_str = jsonpickle.encode(obj, unpicklable=unpicklable, make_refs=make_refs)
    write_to_file(dir_path, file_name, json_str, flags, encoding=encoding)


def read_json(dir_path: Path, file_name: str, flags="r", encoding=ARXIV_ENCODING) -> typing.Any:
    file_path = dir_path / file_name
    content = read(file_path, flags=flags, encoding=encoding)
    if not content:
        return None

    return jsonpickle.decode(content)


def rename_file(dir_path: Path, old_name: str, new_name: str) -> bool:
    old_path = dir_path / old_name
    new_path = dir_path / new_name

    if not old_path.is_file():
        return False

    old_path.replace(new_path)
    return True


def delete_file(file_path: Path) -> None:
    file_path.unlink(missing_ok=True)


def delete_files(file_paths: list[Path]) -> None:
    for file_path in file_paths:
        file_path.unlink(missing_ok=True)


def delete_file_in_dir(dir_path: Path, file_name: str) -> None:
    file_path = dir_path / file_name
    delete_file(file_path)


def _delete_cached_requests() -> None:
    xml_files = [path for path in _REQUESTS_PATH.iterdir() if path.is_file()]
    for xml_file in xml_files:
        xml_file.unlink()


def _delete_recursive(top: Path) -> None:
    # example2 from: https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.walk
    for root, dirs, files in top.walk(top_down=False):
        for name in files:
            (root / name).unlink()
        for name in dirs:
            (root / name).rmdir()


def _delete_arxiv_files() -> None:
    for paper_dir in get_paper_dirs():
        delete_file_in_dir(paper_dir, ARXIV_METADATA_FILE)
        tex_dir = paper_dir / _PAPER_TEX_DIR
        if tex_dir.is_dir():
            _delete_recursive(tex_dir)


def clear_cache() -> None:
    _delete_cached_requests()
    _delete_arxiv_files()
    delete_file_in_dir(get_stats_dir(), ROR_DATASET_FILE)
    delete_file_in_dir(get_papers_dir(), SKIPPED_DL_FILE)


def delete_generated_data() -> None:
    for paper_dir in get_paper_dirs():
        delete_file_in_dir(paper_dir, CMDS_FILE)
        delete_file_in_dir(paper_dir, EXTRACTED_DATA_FILE)
        delete_file_in_dir(paper_dir, MATCHED_DATA_FILE)


def clear_stats() -> None:
    # filled by script export_stats.py
    _delete_recursive(get_stats_dir())


def configure_logger(logger: logging.Logger) -> None:
    # if that logger already has a handler, do not modify it further
    if logger.hasHandlers():
        return

    logger.setLevel(LOG_LEVEL)
    logger.propagate = False  # prevent child loggers from propagating the log to parent logger
    handler = logging.StreamHandler(sys.stdout)  # not great for sysadmins but me like better than stderr :)
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s [%(filename)s#%(funcName)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        style="%"  # f-strings get evaluated even if logging level prevents log anyway, thus use modulo formating
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
