import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util

# these are commands handled elsewhere, and we can ignore them. Commands like \thanks{}, \footnotemark[],
# \footnote{} and \textsuperscript{} can be used for affiliation references but also for further information like
# "equal contribution", "corresponding author", etc. so we do not want to ignore those as they might not be
# related to information about affiliation references.
_INVALID_COMMANDS = [
    r"\addr",
    r"\address",
    r"\affaddr",
    r"\affiliation",
    r"\affiliations",
    r"\affil",
    r"\authorblock",
    r"\ieeeauthorblock",
    r"\ieeeauthorrefmark",
    r"\ieeecompsocitemizethanks",
    r"\institute",
    r"\institution"
]


def _find_authors(part: str) -> list[dict]:
    authors = []
    for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, part):
        name = m.group("name")
        ref = m.group("ref_id").strip("$^{} ")
        if not name or not ref:
            continue

        ref_ids = cmd_util.split_ref_strings(ref)
        authors.append({
            "name": name,
            "ref_id": ref_ids
        })

    return authors


def _find_affiliations(part: str) -> list[dict]:
    affiliations = []
    for m in regex.finditer(reg_exp.MATH_AFFILIATION, part):
        name = m.group("name")
        ref = m.group("ref_id").strip("$^{} ")
        if not name or not ref:
            continue

        affiliations.append({
            "name": name,
            "ref_id": ref
        })

    return affiliations


def _is_possible_author_part(part: str) -> bool:
    if part.endswith("$"):
        return True

    if part.count("$") >= 2:
        # here we do not need another check as the $ are distributed over the whole part anyway (unless single author)
        return True

    return False


def _is_possible_affiliation_part(part: str) -> bool:
    if part.startswith("$"):
        return True

    if part.count("$") == 2:  # would be true on a single name in part: "forename surname$^{1}$ \\"
        # check that the reference occurrs in the first half as affiliations normally have the
        # reference on their left side
        math_index = part.find("$")
        if math_index < len(part) / 2:
            return True

    return False


# split lines on latex newline (\\) and join lines without math mode chars with the previous one.
# this is intended to join parts of affiliation definitions like
# "$^1$Institute Name \\ University Name \\ City Name \\ Country"
# to
# ["$^1$Institute Name \\ University Name \\ City Name \\ Country"]
# instead of
# ["$^1$Institute Name", "University Name", "City Name", "Country"]
def _split_to_math_parts(cmd_content: str) -> list[str]:
    parts = cmd_content.split(r"\\")
    math_parts = []
    buf = ""
    for part in parts[::-1]:
        if part.count("$") == 0:
            buf = part + buf  # prepend part to previously buffered parts
        else:
            math_parts.append((part + buf).strip())
            buf = ""

    if buf:
        math_parts.append(buf.strip())

    return math_parts[::-1]  # reverse list as it would be the wrong way around


class AuthorMathModeAff(SingleCmdScheme):
    """
    After each author there are references to their affiliations in math mode.
    The affiliations have the reference before their name.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        math_mode_char = cmd_content.count("$")
        if math_mode_char == 0 or math_mode_char % 2 == 1:
            return False

        # since some use $ ^{...}$ or ${ }^{...}$ we remove spaces for counting the occurrences
        no_spaces = cmd_content.replace(" ", "")
        math_mode_refs = no_spaces.count("$^") + no_spaces.count("${}^")
        if math_mode_refs < 2:
            return False

        cmd_content = cmd_content.lower()
        for invalid_cmd in _INVALID_COMMANDS:
            if invalid_cmd in cmd_content:
                return False

        # \authorinfo{}{}{} with math mode gets handled elsewhere
        if cmd_name == "authorinfo":
            return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )

        parts = _split_to_math_parts(cmd_content)
        affiliations = []
        authors = []
        for part in parts:
            if _is_possible_affiliation_part(part):
                affiliations += _find_affiliations(part)
            elif _is_possible_author_part(part):
                authors += _find_authors(part)

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
