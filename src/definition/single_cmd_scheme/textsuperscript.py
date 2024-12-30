import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util
from definition.single_cmd_scheme.math_mode import AuthorMathModeAff


def _find_affiliations(pattern: regex.Pattern[str], cmd_content: str) -> list[dict]:
    affiliations = []
    for m in regex.finditer(pattern, cmd_content):
        name = m.group("name").strip()
        ref = m.group("ref")[1:-1].strip()
        if not name or not ref:
            continue

        affiliations.append({
            "name": cmd_util.sanitize(name),
            "ref_id": ref
        })

    return affiliations


def _find_authors(cmd_content: str) -> list[dict]:
    authors = []
    for m in regex.finditer(reg_exp.AUTHOR_TEXTSUPERSCRIPT, cmd_content):
        name = m.group("name")
        ref = m.group("ref")[1:-1].strip()
        if not name or not ref:
            continue

        ref_ids = [sref_id for ref_id in ref.split(",") if len(sref_id := ref_id.strip()) > 0]
        if name.lower().startswith("and "):
            name = name[4:]

        authors.append({
            "name": cmd_util.sanitize(name),
            "ref_id": ref_ids
        })

    return authors


def _sub_ts_math(match: regex.Match[str]) -> str:
    content = match.group("cnt")[1:-1].strip("$, ")
    return f"$^{{{content}}}$"


class AuthorTextSuperScript(SingleCmdScheme):
    r"""
    Each author is followed by \textsuperscript{} with a reference to an affiliation. Each affiliation is preceded by
    \textsuperscript{} with its reference.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\textsuperscript" not in cmd_content:
            return False

        textsuperscript_count = cmd_content.count(r"\textsuperscript")
        return textsuperscript_count >= 2

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.TEXTSUPERSCRIPT_MULTI,
            lambda a, b: rf"\textsuperscript{{{a},{b}}}"
        )

        # translate textsuperscript to math mode and pass to math mode ext
        # they are pretty much the same
        cmd_content = regex.sub(reg_exp.TEXTSUPERSCRIPT_CONTENT, _sub_ts_math, cmd_content)
        return AuthorMathModeAff().extract(cmd_name, cmd_content)


class AuthorDoubleTextSuperScript(SingleCmdScheme):
    r"""
    Each author is followed by \textsuperscript{} with a reference to an affiliation. Each affiliation has its
    reference inside the first argument of \textsuperscript{}{} and its name in the second argument.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\textsuperscript" not in cmd_content:
            return False

        textsuperscript_count = cmd_content.count(r"\textsuperscript")
        if textsuperscript_count <= 2:
            return False

        return bool(regex.search(reg_exp.DOUBLE_TEXTSUPERCRIPT_AFFILIATION, cmd_content))

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.TEXTSUPERSCRIPT_MULTI,
            lambda a, b: rf"\textsuperscript{{{a},{b}}}"
        )
        authors = _find_authors(cmd_content)
        affiliations = _find_affiliations(reg_exp.DOUBLE_TEXTSUPERSCRIPT_AFFILIATION_CONTENT, cmd_content)
        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class AuthorTextSuperScriptNameAffil(SingleCmdScheme):
    r"""
    Each author is inside \name{} with a reference to an affiliation using \textsuperscript{}.
    Affiliations are inside \affil{} and are each preceded by \textsuperscript{} with their reference.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\textsuperscript" not in cmd_content:
            return False

        textsuperscript_count = cmd_content.count(r"\textsuperscript")
        if textsuperscript_count <= 2:
            return False

        cmd_content = cmd_content.lower()
        return r"\name" in cmd_content and r"\affil{" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        names_match = regex.search(reg_exp.NAME_CONTENT, cmd_content)
        if not names_match:
            return []

        affil_match = regex.search(reg_exp.AFFIL_CONTENT, cmd_content)
        if not affil_match:
            return []

        name_content = names_match.group("cnt")[1:-1].strip()
        name_content = cmd_util.join_multi_cmd_occurrences(
            name_content, reg_exp.TEXTSUPERSCRIPT_MULTI,
            lambda a, b: rf"\textsuperscript{{{a},{b}}}"
        )

        authors = _find_authors(name_content)
        affil_content = affil_match.group("cnt")[1:-1].strip()
        affiliations = []
        for aff_part in cmd_util.split_ref_commands(r"\textsuperscript", affil_content):
            m = regex.search(reg_exp.AFFILIATION_TEXTSUPERSCRIPT, aff_part)
            if not m:
                continue

            ref = m.group("ref")[1:-1].strip()
            name = m.group("name")
            affiliations.append({
                "name": cmd_util.sanitize(name),
                "ref_id": ref,
            })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
