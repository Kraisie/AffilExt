import logging
import time
import zipfile
from pathlib import Path

import requests

import util
from definition.data.RorDataset import ResearchLocation, RorDataset, ResearchOrganization

_RECORD_LIST_URL = "https://zenodo.org/api/communities/ror-data/records?q=&sort=newest"
_MAX_RETRIES = 10
_ATTEMPT_DELAY_SEC = 10

_logger: logging.Logger = logging.getLogger(__name__)


def _get_latest_release_info() -> tuple[str, str]:
    _logger.info("Retrieving ROR dataset release information...")
    retries = 1
    while True:
        ror_records = requests.get(_RECORD_LIST_URL).json()
        first_hit = ror_records.get("hits", {}).get("hits", [{}])[0]
        file = first_hit.get("files", {})[0]
        download_file_name = file.get("key", None)
        download_url = file.get("links", {}).get("self", None)
        if not download_url or not download_file_name:
            if retries > _MAX_RETRIES:
                _logger.error("Exceeded amount of max retries! Stopping ROR download.")
                return "", ""

            retries += 1
            _logger.warning(
                "Request for ROR dataset download URL failed. Starting attempt %s in %s seconds.",
                retries, _ATTEMPT_DELAY_SEC
            )
            time.sleep(_ATTEMPT_DELAY_SEC)
        else:
            break

    _logger.info("Retrieved latest ROR dataset information!")
    return download_file_name, download_url


def _download_dataset(ror_dir: Path, file_name: str, latest_dl_url: str) -> bool:
    _logger.info("Downloading latest ROR dataset...")
    retries = 1
    while True:
        response = requests.get(latest_dl_url)
        if not response or response.status_code != 200 or not (content := response.content):
            if retries > _MAX_RETRIES:
                _logger.error("Exceeded amount of max retries! Stopping ROR download.")
                return False

            retries += 1
            _logger.warning(
                "Download for ROR dataset failed. Starting attempt %s in %s seconds.",
                retries, _ATTEMPT_DELAY_SEC
            )
            time.sleep(_ATTEMPT_DELAY_SEC)
            continue

        util.write_to_file(ror_dir, file_name, content, flags="wb", encoding=None)
        break

    _logger.info("Finished downloading ROR dataset.")
    return True


def _extract_dataset_file(ror_dir: Path, zip_file_name: str, dataset_file_name: str) -> None:
    _logger.info("Extracting ROR files from zip.")
    zip_path = ror_dir / zip_file_name
    with zipfile.ZipFile(zip_path, "r") as z:
        if dataset_file_name in z.namelist():  # should exist, otherwise we have a problem
            z.extract(dataset_file_name, path=ror_dir)
        else:
            _logger.info(
                "ROR dataset file '%s' does not exist in zip file. Extracting all contents instead!",
                dataset_file_name
            )
            z.extractall(ror_dir)

    util.delete_file_in_dir(ror_dir, zip_file_name)


def _find_dataset_file(ror_dir: Path) -> str:
    _logger.warning("ROR dataset file not found, searching for it...")
    files = util.get_all_files_recursive(ror_dir, extension=".json")
    for file in files:
        if "schema_v2" in file.name:
            _logger.info("Found ROR dataset file '%s'.")
            return file.name

    return ""


def _get_org_names(org: dict) -> list[str]:
    org_names = org.get("names", [])
    names = []
    for name in org_names:
        # some companies have really short names like "AI Corporation (United Kingdom)" has another
        # name that is not listed as acronym "ai". That is bad for later matching so we require
        # at least 5 characters (this will remove 0.67% of the total names and most acronyms)
        if len(name_value := name.get("value", "")) > 4:
            names.append(name_value)

    return names


def _get_org_location(org: dict) -> list[ResearchLocation]:
    org_locations = org.get("locations", [])
    locations = []
    for location in org_locations:
        geo_details = location.get("geonames_details", {})
        location_name = geo_details.get("name", "")
        location_country = geo_details.get("country_name", "")
        locations.append(ResearchLocation(location_name, location_country))

    return locations


def _minimize_dataset(ror_dir: Path, dataset_file: str) -> RorDataset:
    dataset = util.read_json(ror_dir, dataset_file)
    # add a fallback as first element as empty strings will just match the first element
    research_organizations = [ResearchOrganization(
        "https://ror.org",
        ["Incredibly unlikely match for anything, not supposed to be a real match!"],
        []  # locations
    )]
    for research_org in dataset:
        ror_id = research_org["id"]
        names = _get_org_names(research_org)
        locations = _get_org_location(research_org)
        research_organizations.append(ResearchOrganization(ror_id, names, locations))

    return RorDataset(dataset_file, research_organizations)


def _remove_unused_files(ror_dir: Path):
    files = [file for file in util.get_all_files_recursive(ror_dir) if file.name != util.ROR_DATASET_FILE]
    util.delete_files(files)
    _logger.info("Removed unused ROR dataset files.")


def _is_latest_version_on_disk(ror_dir: Path, dataset_file_name: str):
    if not util.file_exists(ror_dir, util.ROR_DATASET_FILE):
        return False

    # TODO: this could be improved by not reading the whole file
    dataset: RorDataset = util.read_json(ror_dir, util.ROR_DATASET_FILE)
    return dataset.src_file_name == dataset_file_name


def prepare_dataset():
    ror_dir = util.get_ror_dir()
    zip_file_name, latest_dl_url = _get_latest_release_info()
    if not zip_file_name or not latest_dl_url:
        return

    base_name = zip_file_name.removesuffix(".zip")
    dataset_file_name = f"{base_name}_schema_v2.json"
    if _is_latest_version_on_disk(ror_dir, dataset_file_name):
        _logger.info("Found latest ROR dataset file on disk! Skipping download.")
        return

    if not _download_dataset(ror_dir, zip_file_name, latest_dl_url):
        return

    _extract_dataset_file(ror_dir, zip_file_name, dataset_file_name)
    if not util.file_exists(ror_dir, dataset_file_name):
        if not (dataset_file_name := _find_dataset_file(ror_dir)):
            _logger.error("Could not retrieve ROR dataset!")
            return

    min_dataset = _minimize_dataset(ror_dir, dataset_file_name)
    util.write_obj_to_json(ror_dir, util.ROR_DATASET_FILE, min_dataset)
    _logger.info("ROR dataset prepared!")
    _remove_unused_files(ror_dir)
