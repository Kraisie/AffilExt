"""
Benchmark parts of the program
"""
import random
import timeit
from pathlib import Path
from typing import Callable

import extract_author_aff
import extract_cmds
import util

_seed = "benchmark1337"
_choices = {
    "cmds": {
        "f": extract_cmds.run,
        "validator": lambda paper_dir: len(util.get_all_tex_files(paper_dir / util._PAPER_TEX_DIR)) > 0
    },
    "aff": {
        "f": extract_author_aff.run,
        "validator": lambda paper_dir: util.file_exists(paper_dir, util.CMDS_FILE)
    }
}


def _benchmark(f: Callable, paper_dirs: list[Path], runs: int) -> None:
    # unfortunately timeit does not support running src between runs. setup only runs before the first run.
    # since we need to remove the created files we will need to run in a loop ourselves.
    timings = []
    for _ in range(runs):
        util.delete_generated_data()
        t = timeit.timeit(lambda: f(paper_dirs), number=1)
        timings.append(t)

    print(f"{runs} runs with {len(paper_dirs)} papers:\n\tmin: {min(timings)} seconds\n\t"
          f"avg: {sum(timings) / len(timings)} seconds\n\tmax: {max(timings)} seconds")


def _select_papers(method_info: dict, sample_size: int) -> list[Path]:
    random.seed(_seed)
    paper_dirs = util.get_paper_dirs()

    if len(paper_dirs) <= sample_size:
        print(f"Sample size is bigger than available papers! Selected all {len(paper_dirs)} papers.")
        return list(paper_dirs)

    if len(paper_dirs) < sample_size * 3:
        # Collisions on random selection and all that
        print(f"With {len(paper_dirs)} papers, {sample_size} is a large sample size. Consider using a smaller sample size.")

    # do it manually as random.choices() will not consider whether that paper is valid for the method
    papers = set()
    while len(papers) < sample_size:
        rdm_index = random.randrange(len(paper_dirs))
        if method_info.get("validator")(paper_dirs[rdm_index]):
            papers.add(paper_dirs[rdm_index])

    return list(papers)


def main():
    method = None
    sample_size = 500
    runs = 10
    sample_size_str = input(f"Select the sample size (default: {sample_size}): ")
    sample_size = int(sample_size_str) if (sample_size_str and sample_size_str.isdigit()) else sample_size
    runs_str = input(f"Select how many times to run the method (default: {runs}): ")
    runs = int(runs_str) if (runs_str and runs_str.isdigit()) else runs

    while not method:
        selection = input(f"Please select what to benchmark {[choice for choice in _choices.keys()]}: ")
        method = _choices.get(selection, None)

    paper_dirs = _select_papers(method, sample_size)
    _benchmark(method.get("f"), paper_dirs, runs)


if __name__ == '__main__':
    main()
