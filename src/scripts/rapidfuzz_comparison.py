"""
Compare the different ratios that the RapidFuzz library offers for fuzzy string matching.
"""
import random
import timeit

from rapidfuzz import fuzz, utils, process

import threaded_run
import util
from definition.data.ExtAuthorData import ExtAuthorInfo
from definition.data.RorDataset import ResearchOrganization

_RUNS = 5
_SCORERS = [
    ("ratio", fuzz.ratio),
    ("partial_ratio", fuzz.partial_ratio),
    ("token_set_ratio", fuzz.token_set_ratio),
    ("partial_token_set_ratio", fuzz.partial_token_set_ratio),
    ("token_sort_ratio", fuzz.token_sort_ratio),
    ("partial_token_sort_ratio", fuzz.partial_token_sort_ratio),
    ("token_ratio", fuzz.token_ratio),
    ("partial_token_ratio", fuzz.partial_token_ratio),
    ("WRatio", fuzz.WRatio)
]


def _calc_rf_ratios(affiliation: str, args: tuple) -> None:
    ror_orgs: list[str] = args[0]
    score_strs = [f"\noriginal: '{affiliation}'"]
    for scorer in _SCORERS:
        ror, score, _ = process.extractOne(affiliation, ror_orgs, scorer=scorer[1], processor=utils.default_process)
        score_strs.append(f"\t{scorer[0]}: '{ror}' with {score}")

    print("\n".join(score_strs))


def _get_affiliations(ext_data: ExtAuthorInfo):
    extractions = ext_data.extractions
    affiliations = []
    for extraction in extractions:
        for author in extraction.authors:
            affiliations += author.affiliations

    return affiliations


def _select_random_affiliations(n=100) -> set[str]:
    paper_dirs = util.get_paper_dirs()
    affiliations = set()
    while len(affiliations) < n:
        choice = random.choice(paper_dirs)
        ext_data = util.read_json(choice, util.EXTRACTED_DATA_FILE)
        if not ext_data:
            paper_dirs.remove(choice)
            continue

        ext_affiliations = _get_affiliations(ext_data)
        for ext_affiliation in ext_affiliations:
            affiliations.add(ext_affiliation)

        paper_dirs.remove(choice)

    return affiliations


def _get_ror_names(research_orgs: list[ResearchOrganization]) -> list[str]:
    org_names = []
    for research_org in research_orgs:
        for name in research_org.names:
            org_names.append(name)

    return org_names


def _get_ror_orgs():
    ror_dataset = util.read_json(util.get_ror_dir(), util.ROR_DATASET_FILE)
    return _get_ror_names(ror_dataset.data)


def _run_score_test(affiliations: set[str], ror_orgs: list[str]) -> None:
    threaded_run.run(affiliations, _calc_rf_ratios, ror_orgs)


def _run_time_test_scorer(affiliations: set[str], ror_orgs: list[str], scorer: callable) -> None:
    for affiliation in affiliations:
        a, b, c = process.extractOne(affiliation, ror_orgs, scorer=scorer, processor=utils.default_process)


def _run_time_test(affiliations: set[str], ror_orgs: list[str]):
    times = []
    for scorer in _SCORERS:
        t = timeit.timeit(lambda: _run_time_test_scorer(affiliations, ror_orgs, scorer[1]), number=_RUNS)
        times.append(t)
        print(f"{scorer[0]}: {t} secs")

    max_time = max(times)
    normalized_times = [time / max_time for time in times]
    print()
    for norm_time, scorer in zip(normalized_times, _SCORERS):
        print(f"normalized time of {scorer[0]}: {norm_time}")


def main():
    print("Reading files...")
    ror_orgs = _get_ror_orgs()
    affiliations = _select_random_affiliations()
    print("Running score test...")
    _run_score_test(affiliations, ror_orgs)
    print(
        f"Running time test with {len(affiliations)} affiliations, "
        f"{len(ror_orgs)} ROR organization names "
        f"and {_RUNS} runs per scorer..."
    )
    _run_time_test(affiliations, ror_orgs)


if __name__ == '__main__':
    main()
