import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


class AuthorInfoSingle(SingleCmdScheme):
    r"""
    Using the \authorinfo{}{}{}, \oneauthor{}{}{} or \towauthors{}{}{} command. First {} is for the name of the
    author(s). Second {} is for the affiliation and the third {} is for the email (not included here).
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        if cmd_name not in ["twoauthors", "oneauthor", "authorinfo"]:
            return False

        cmd_content = cmd_content.lower()
        return bool(regex.search(reg_exp.EXT_AUTHORINFO, cmd_content))

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        if not (m := regex.search(reg_exp.EXT_AUTHORINFO, cmd_content)):
            return []

        name = m.group("name")[1:-1]
        aff = m.group("aff")[1:-1]
        affiliation = cmd_util.sanitize(aff)
        names = reg_exp.split_on_separator(name)
        return [Author(cmd_util.sanitize(name), [affiliation]) for name in names]


class AuthorInfoMath(SingleCmdScheme):
    r"""
    Using the \authorinfo{}{}{} command. First {} is for the names of the authors.
    The names can be separated by a few different separators.
    Second {} is for the affiliation and applies to all names in that command.
    The third {} is for the email (not included here).
    References between authors and affiliations are written in math mode.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        if cmd_name != "authorinfo":
            return False

        return bool(regex.search(reg_exp.MATH_MODE_CONTENT, cmd_content))

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        if not (m := regex.search(reg_exp.EXT_AUTHORINFO, cmd_content)):
            return []

        names_str = m.group("name")[1:-1].strip()
        name_parts = reg_exp.split_on_separator(names_str)
        authors = []
        for name_part in name_parts:
            ref_match = regex.search(reg_exp.MATH_MODE_CONTENT, name_part)
            if not ref_match:
                continue

            ref_content = ref_match.group("cnt").strip("{}^ ")
            ref_ids = cmd_util.split_ref_strings(ref_content)
            authors.append({
                "name": name_part.replace(ref_match.group(0), ""),
                "ref_id": ref_ids
            })

        affiliation_str = m.group("aff")[1:-1].strip()
        affiliations = []
        for m in regex.finditer(reg_exp.MATH_AFFILIATION, affiliation_str):
            name = m.group("name")
            ref_id = m.group("ref_id").strip("$^{} ")
            affiliations.append({
                "name": name,
                "ref_id": ref_id,
            })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
