import argparse
import logging
import multiprocessing
from pathlib import Path

import bs4
import requests

import download
import extract_author_aff
import extract_cmds
import match_data
import ror_dl
import threaded_log
import util
from ArgRange import ArgRange
from ArxivAPI import ArxivAPI

_logger: logging.Logger = logging.getLogger(__name__)


def _query_arxiv_api(arxiv_api: ArxivAPI, args: argparse.Namespace) -> list[bs4.Tag]:
    logger = logging.getLogger(__name__)
    logger.info("Sending ArXiv query... ")
    feed_entries = arxiv_api.query(args.category, args.max_results, args.chunk_size)
    logger.info("Received %s of %s requested entries.", len(feed_entries), args.max_results)
    return feed_entries


# There are quite a few dataset for research organizations:
# - ERA Partnership Organisations: https://www.era-learn.eu/network-information/organisations
# - eqar Higher Education Institutions: https://www.eqar.eu/qa-results/download-data-sets/
# - US Colleges and Universities: https://public.opendatasoft.com/explore/dataset/us-colleges-and-universities/table/
# - Times Higher Education World University Rankings: https://www.kaggle.com/datasets/ddosad/timesworlduniversityrankings2024
# - "All The Universities In The World": https://www.kaggle.com/datasets/thedevastator/all-universities-in-the-world
# However, the Research Organization Registry (ROR) seems to be the most extensive by quite some margin.
# Source: https://ror.org/registry/
# Data URL: https://zenodo.org/records/14188848
def _download_ror_dataset(logging_queue: multiprocessing.Queue) -> None:
    threaded_log.configure_process_logger(logging_queue)
    ror_dl.prepare_dataset()


def _download_arxiv(args: argparse.Namespace, logging_queue: multiprocessing.Queue) -> None:
    threaded_log.configure_process_logger(logging_queue)
    logger = logging.getLogger(__name__)
    arxiv_api = ArxivAPI()
    if not args.kaggle_path:
        logger.info("Running download via ArXiv API.")
        feed_entries = _query_arxiv_api(arxiv_api, args)
        download.run_api(arxiv_api, feed_entries)
    else:
        logger.info("Running download via Kaggle import.")
        kaggle_path = Path(args.kaggle_path)
        download.run_kaggle(arxiv_api, kaggle_path, args.category)


def _run_downloads(args: argparse.Namespace) -> None:
    log_queue = multiprocessing.Queue()
    p_ror = multiprocessing.Process(target=_download_ror_dataset, args=[log_queue], daemon=True)
    p_arxiv = multiprocessing.Process(target=_download_arxiv, args=[args, log_queue], daemon=True)

    logging_thread = threaded_log.start_logging_thread(log_queue)
    p_ror.start()
    p_arxiv.start()

    p_ror.join()
    p_arxiv.join()
    log_queue.put(None)
    logging_thread.join()
    _logger.info("Finished all downloads!")


def _perform_requested_actions(args: argparse.Namespace) -> None:
    _perform_clear_actions(args)
    if args.mode == "download" or args.mode == "all":
        _run_downloads(args)

    if args.mode == "extract" or args.mode == "all":
        paper_dirs = util.get_paper_dirs()
        _logger.info("Extracting commands...")
        extract_cmds.run(paper_dirs)
        _logger.info("Finished extracting commands! Extracting author affiliations...")
        extract_author_aff.run(paper_dirs)
        _logger.info("Finished extracting author affiliations! Matching data...")
        match_data.run(paper_dirs)
        _logger.info("Done!")


def _perform_clear_actions(args: argparse.Namespace) -> None:
    if args.clear_cache:
        util.clear_cache()
        _logger.info("Cache cleared.")

    if args.clear_metadata:
        util.delete_generated_data()
        _logger.info("Metadata cleared.")


def _build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        description="Downloads papers from an ArXiv category, downloads source files and extracts authors and affiliations."
    )

    arg_parser.add_argument(
        "mode",
        action="store",
        choices=["download", "extract", "all"],
        default="all",
        help="Choose whether to download papers only, extract LaTeX commands used for author and affiliation definitions, or both. Default: 'all'.",
        metavar="MODE"
    )
    arg_parser.add_argument(
        "-c", "--category",
        action="store",
        dest="category",
        default="cs.SE",
        help="The ArXiv category from which articles are downloaded. Works for both API download and Kaggle import. Use 'all' to use all entries of the Kaggle dataset, no matter the category. Default: 'cs.SE'.",
        metavar="\"CAT\""
    )
    arg_parser.add_argument(
        "-r", "--max_results",
        action=ArgRange,
        default=200,
        dest="max_results",
        help="Maximum number of papers to download. Has to be between 1 and 30_000 (inclusive). Default: 200.",
        metavar="N",
        min=1,
        max=30000
    )
    arg_parser.add_argument(
        "-s", "--chunk-size",
        action=ArgRange,
        default=500,
        dest="chunk_size",
        help="Number of paper metadata entries to request from the API at once. Has to be between 10 and 1000 (inclusive). Default: 500.",
        metavar="S",
        min=10,
        max=1000
    )
    arg_parser.add_argument(
        "-k", "--kaggle",
        action="store",
        dest="kaggle_path",
        help="The path to the Kaggle arXiv dataset file. This will use the Kaggle file instead of the arXiv API.",
        metavar="PATH"
    )
    arg_parser.add_argument(
        "--clear-cache",
        action="store_true",
        dest="clear_cache",
        help="Deletes all files related to arXiv (arXiv metadata, latex files) and the ROR dataset. Also removes the list of papers to skip downloading."
    )
    arg_parser.add_argument(
        "--clear-metadata",
        action="store_true",
        dest="clear_metadata",
        help="Deletes all previously generated data before running."
    )

    return arg_parser


def _get_cl_args() -> argparse.Namespace:
    arg_parser = _build_arg_parser()
    return arg_parser.parse_args()


def _verify_kaggle_path(kaggle_path: str) -> bool:
    if not kaggle_path:
        return False

    file_path = Path(kaggle_path)
    return file_path.is_file()


def _verify_category(args: argparse.Namespace) -> bool:
    category = args.category
    if category == "all" and args.kaggle_path:
        return True

    # do not use export.arxiv.org as that will return 200 even if the category does not exist
    url = f"https://arxiv.org/list/{category}/recent"
    response = requests.head(url)
    _logger.debug("Categoy verification status code: %s", response.status_code)
    return response.status_code == 200


def main():
    util.configure_logger(_logger)
    args = _get_cl_args()
    if not _verify_category(args):
        _logger.error("Could not verify existence of category. Please validate the category name: '%s'", args.category)
        return

    if args.kaggle_path and not _verify_kaggle_path(args.kaggle_path):
        _logger.error("Invalid Kaggle dataset file path: '%s'", args.kaggle_path)
        return

    _logger.debug("Running download script with args: %s", args)
    _perform_requested_actions(args)


if __name__ == "__main__":
    main()
