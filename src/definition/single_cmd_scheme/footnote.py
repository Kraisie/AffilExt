import regex

from definition import latex
from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _extract_authors_from_part(part: str) -> list[dict]:
    authors = []
    subparts = reg_exp.split_on_separator(part)
    for subpart in subparts:
        for m in regex.finditer(reg_exp.FOOTNOTEMARK_AUTHOR, subpart):
            name = m.group("name")
            ref_id = m.group("ref_id")
            ref_ids = [sref for ref in ref_id.split(",") if len(sref := ref.strip()) > 0]
            authors.append({
                "name": name,
                "ref_id": ref_ids,
            })

    return authors


def _extract_affiliations_from_part(part: str) -> list[dict]:
    affiliations = []
    for m in regex.finditer(reg_exp.FOOTNOTEMARK_AFFILIATION, part):
        name = m.group("name")
        ref_id = m.group("ref_id")
        affiliations.append({
            "name": name,
            "ref_id": ref_id,
        })

    return affiliations


class FootnoteMark(SingleCmdScheme):
    r"""
    Each author has a \footnotemark[] that references their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        if r"\footnotemark" not in cmd_content:
            return False

        refs = {}
        for m in regex.finditer(reg_exp.FOOTNOTEMARK_CONTENT, cmd_content):
            ref = m.group(1)
            if ref not in refs:
                refs[ref] = 1
            else:
                refs[ref] += 1

        if not refs:
            return False

        # each ref has to occur at least twice (once on author, once on affiliation)
        for occurrences in refs.values():
            if occurrences < 2:
                return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.FOOTNOTEMARK_MULTI,
            lambda a, b: fr"\footnotemark[{a},{b}]"
        )

        authors = []
        affs = []
        parts = cmd_content.split(r"\\")
        for part in parts:
            part = part.strip("{ ")
            if part.startswith(r"\footnotemark"):
                affs += _extract_affiliations_from_part(part)
            else:
                authors += _extract_authors_from_part(part)

        return cmd_util.join_author_and_affil_by_id(authors, affs)


class Footnote(SingleCmdScheme):
    r"""
    Each author name is followed by a \footnote{} that includes their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\footnotemark" in cmd_content:
            return False

        return r"\footnote" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_content = latex.remove_latex_newlines(cmd_content)
        author_affs = []
        for m in regex.finditer(reg_exp.EXT_AUTHOR_FOOTNOTE, cmd_content):
            name = m.group("name").strip()
            affiliation = m.group("aff")[1:-1].strip()
            author_affs.append(Author(name, [affiliation]))

        return author_affs
