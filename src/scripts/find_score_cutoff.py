import util
from definition.data.MatchedAuthorData import MatchedPaperData, MatchedAuthorInfo

_CHUNK_SIZE = 10
_SCORE_POINTS = [95, 85, 75, 65, 55, 45, 35, 25, 15, 5]


def _check_chunk(name_matchings: list[tuple[str, float]], index: int) -> str:
    correct = 0
    skipped = 0  # e.g. when the extraction is faulty so a matching has no useful data
    total = 0
    end = min(len(name_matchings), index + _CHUNK_SIZE)
    for i in range(index, end):
        name_matching = name_matchings[i]
        print(f"{i} - {name_matching}")
        answer = input("Is this matching correct? [yes/no/skip]: ")
        if answer is not None and len(answer) > 0:
            match answer.lower()[0]:
                case "y":
                    correct += 1
                case "s":
                    skipped += 1
                case "n" | _:
                    pass

        total += 1

    return f"{(correct / (total - skipped)) * 100:.2f}% ({skipped} skipped)"


def _check_matchings(name_matchings: list[tuple[str, float]]) -> list[str]:
    chunk_ratings = []
    block = 0
    for i in range(len(name_matchings)):
        score = int(name_matchings[i][1])
        if score != _SCORE_POINTS[block]:
            if score < _SCORE_POINTS[block]:
                block += 1

            continue

        correct_matchings = _check_chunk(name_matchings, i)
        chunk_ratings.append(f"Top {i} to {i + _CHUNK_SIZE} are {correct_matchings} correct")
        block += 1
        if block >= len(_SCORE_POINTS):
            break

    return chunk_ratings


def _get_aff_matchings(authors: list[MatchedAuthorInfo]) -> list[tuple[str, float]]:
    encountered_matches = set()
    aff_matchings = []
    for author in authors:
        aff_matching = author.affiliations
        for aff_match in aff_matching:
            match = f"'{aff_match.ext_name}' <-> {aff_match.matched_ror}"
            if match in encountered_matches:
                continue

            aff_matchings.append((match, aff_match.score))
            encountered_matches.add(match)

    return sorted(aff_matchings, key=lambda x: -x[1])


def _get_name_matchings(authors: list[MatchedAuthorInfo]) -> list[tuple[str, float]]:
    encountered_matches = set()
    name_matchings = []
    for author in authors:
        match = f"'{author.arxiv_name}' <-> '{author.ext_name}'"
        if match in encountered_matches:
            continue

        name_matchings.append((match, author.score))
        encountered_matches.add(match)

    return sorted(name_matchings, key=lambda x: -x[1])


def _get_matched_data() -> list[MatchedAuthorInfo]:
    authors = []
    for paper_dir in util.get_paper_dirs():
        matched: MatchedPaperData = util.read_json(paper_dir, util.MATCHED_DATA_FILE)
        if not matched:
            continue

        authors += matched.matched_authors

    return authors


def _affs(matched_data: list[MatchedAuthorInfo]):
    aff_matchings = _get_aff_matchings(matched_data)
    aff_chunks = _check_matchings(aff_matchings)
    print(f"\n[AFF STATS]")
    for aff_chunk, score_point in zip(aff_chunks, _SCORE_POINTS):
        print(f"[{score_point}] {aff_chunk}")


def _names(matched_data: list[MatchedAuthorInfo]):
    name_matchings = _get_name_matchings(matched_data)
    name_chunks = _check_matchings(name_matchings)
    print(f"\n[NAME STATS]")
    for name_chunk, score_point in zip(name_chunks, _SCORE_POINTS):
        print(f"[{score_point}] {name_chunk}")


def _both(matched_data: list[MatchedAuthorInfo]):
    _names(matched_data)
    _affs(matched_data)


def main():
    mode = input("Check names, affiliations or both? [n/a/b]: ")
    if not mode:
        return

    matched_data = _get_matched_data()
    match mode.lower()[0]:
        case "b":
            _both(matched_data)
        case "n":
            _names(matched_data)
        case "a":
            _affs(matched_data)
        case "_":
            print("No valid selection!")


if __name__ == '__main__':
    main()
