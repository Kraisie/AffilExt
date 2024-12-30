import regex

from definition import reg_exp, latex
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


class NameAffiliation(SingleCmdScheme):
    r"""
    The author names are followed by an \affiliation{} or \affiliations{} which contains their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\sup" in cmd_content or r"\authorname" in cmd_content:
            return False

        if r"\affiliations" in cmd_content:
            return False

        return r"\affiliation" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = latex.remove_latex_newlines(cmd_content[1:-1].strip())
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AFFILIATION_MULTI,
            lambda a, b: fr"\affiliation{{{a}, {b}}}"
        )
        author_aff = []
        for m in regex.finditer(reg_exp.NAME_AFFILIATION, cmd_content):
            name_part = m.group("name")
            names = reg_exp.split_on_separator(name_part)
            affiliation = cmd_util.sanitize(m.group("aff")[1:-1].strip())
            for name in names:
                author_aff.append(Author(cmd_util.sanitize(name), [affiliation]))

        return author_aff


class AffiliationMath(SingleCmdScheme):
    r"""
    The author names are listed first with a reference in math mode.
    The affiliations are in \affiliation{} and also have a reference in math mode.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\sup" in cmd_content or r"\authorname" in cmd_content:
            return False

        if r"\affiliations" in cmd_content:
            return False

        if r"\affiliation" not in cmd_content:
            return False

        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs == 0:
            return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = latex.remove_latex_newlines(cmd_content[1:-1].strip())
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AFFILIATION_MULTI,
            lambda a, b: fr"\affiliation{{{a}, {b}}}"
        )

        affiliations = []
        for m in regex.finditer(reg_exp.AFFILIATION_CONTENT, cmd_content):
            cmd_content = cmd_content.replace(m.group(0), "")
            aff_content = m.group("cnt")[1:-1].strip()
            for n in regex.finditer(reg_exp.MATH_AFFILIATION, aff_content):
                ref = n.group("ref_id").strip("$^{} ")
                name = n.group("name")
                affiliations.append({
                    "name": name,
                    "ref_id": ref
                })

        authors = []
        for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, cmd_content):
            ref = m.group("ref_id").strip("$^{} ")
            name = m.group("name")
            authors.append({
                "name": name,
                "ref_id": cmd_util.split_ref_strings(ref)
            })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class Affiliations(SingleCmdScheme):
    r"""
    The author names are listed first with a reference in math mode.
    The name part and the affiliation part are split by \affiliations.
    The affiliations also have a reference in math mode.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\affiliations" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )

        parts = cmd_content.split(r"\affiliations")
        authors = []
        for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, parts[0]):
            ref = m.group("ref_id").strip("$^{} ")
            name = m.group("name")
            authors.append({
                "name": name,
                "ref_id": cmd_util.split_ref_strings(ref)
            })

        affiliations = []
        for part in parts[1:]:
            for m in regex.finditer(reg_exp.MATH_AFFILIATION, part):
                ref = m.group("ref_id").strip("$^{} ")
                name = m.group("name")
                affiliations.append({
                    "name": name,
                    "ref_id": ref
                })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
