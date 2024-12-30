"""
Manually evaluate the extraction results.
"""
import pathlib
import random
import webbrowser

import tiktoken

import util
from definition.data.ExtCmdData import ExtCmdData
from definition.data.MatchedAuthorData import MatchedPaperData

_SAMPLE_SIZE = 100
_AI_MODEL_IDENTIFIER = ""


def _eval(question: str, stats: dict) -> None:
    while result := input(f"{question} ([Y]es/[N]o/[M]inor mistakes/[I]dentities only/[A]ffiliations only): "):
        match result.upper():
            case "Y":
                stats["correct_data"] += 1
                break
            case "N":
                stats["wrong_data"] += 1
                break
            case "I":
                stats["only_names_correct"] += 1
                break
            case "A":
                stats["only_affiliations_correct"] += 1
                break
            case "M":
                stats["mistake"] += 1
                break
            case "Q":
                raise KeyboardInterrupt
            case _:
                continue


def _get_tokens(instruction: str) -> int:
    encoding = tiktoken.encoding_for_model("gpt-4o")
    return len(encoding.encode(instruction))


def _eval_ai_answer(paper_dir: pathlib.Path, ai_stats: dict):
    # I would use the OpenAI API, but I do not own a credit card :c
    # to estimate the tokens we use tiktoken as OpenAI recommends on their website
    # -> https://platform.openai.com/tokenizer
    ext_cmds: ExtCmdData = util.read_json(paper_dir, util.CMDS_FILE)
    cmd = " ".join([c.original_cmd for c in ext_cmds.cmds])
    ai_instruction = f"""Reply with the authors and their affiliations in the following format:
´´´
Author name: <name>
    Affiliations: <affiliation1>, <affiliation2>
´´´
Extract the data from: 
'{cmd}'"""

    ai_stats["in_tokens"] += _get_tokens(ai_instruction)
    print(f"Copy the following into your choice of AI:\n{ai_instruction}\n")
    _eval("Is the response of the AI correct?", ai_stats)
    response_tokens = input("How many tokens are in the reply? ")
    ai_stats["out_tokens"] += int(response_tokens)


def _manual_eval(arxiv_id: str, stats: dict) -> None:
    webbrowser.open(f"https://arxiv.org/pdf/{arxiv_id}", new=2)
    _eval("Is this correct?", stats)


def _evaluate(paper_dirs: list[pathlib.Path], stats: dict, ai_stats: dict) -> None:
    for paper_dir in paper_dirs:
        matched_data: MatchedPaperData = util.read_json(paper_dir, util.MATCHED_DATA_FILE)
        if not matched_data:
            print(f"Skipping {paper_dir.name} due to missing matched data.")
            continue

        matched_authors = matched_data.matched_authors
        if not matched_authors or len(matched_authors) == 0:
            print(f"Skipping {paper_dir.name} due to missing/empty author list.")
            continue

        print(f"\n--- {paper_dir.name} ---")
        for author in matched_authors:
            print(f"Author (arxiv <-> ext): '{author.arxiv_name}' <-> '{author.ext_name}'")
            print("Affiliations (ext):")
            for affiliation in author.affiliations:
                print(f"\t'{affiliation.ext_name}'")

        _manual_eval(paper_dir.name, stats)
        _eval_ai_answer(paper_dir, ai_stats)


def _select_papers() -> list[pathlib.Path]:
    paper_dirs = util.get_paper_dirs()
    selected = []
    while len(selected) < _SAMPLE_SIZE:
        paper = random.choice(paper_dirs)
        if util.file_exists(paper, util.MATCHED_DATA_FILE):
            selected.append(paper)
            paper_dirs.remove(paper)

    return selected


def main():
    papers = _select_papers()
    self_stats = {
        "wrong_data": 0,
        "mistake": 0,
        "only_names_correct": 0,
        "only_affiliations_correct": 0,
        "correct_data": 0
    }
    ai_stats = {
        "in_tokens": 0,
        "out_tokens": 0,
        "wrong_data": 0,
        "mistake": 0,
        "only_names_correct": 0,
        "only_affiliations_correct": 0,
        "correct_data": 0
    }

    try:
        _evaluate(papers, self_stats, ai_stats)
    finally:
        # print on Quit/KeyboardInterrupt
        print(f"\n\nResults: \n{self_stats}\n{ai_stats}")


if __name__ == "__main__":
    main()
