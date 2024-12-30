import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _ext_multi_aff(cmd_content: str) -> list[Author]:
    authors = []
    for m in regex.finditer(reg_exp.AUTHORNAME_CONTENT, cmd_content):
        name_content = m.group("cnt")[1:-1].strip()
        for n in regex.finditer(reg_exp.NAME_SUP, name_content):
            name = n.group("name")
            ref = n.group("ref")[1:-1].strip()
            ref_ids = cmd_util.split_ref_strings(ref)
            authors.append({
                "name": cmd_util.sanitize(name),
                "ref_id": ref_ids,
            })

    affiliations = []
    for m in regex.finditer(reg_exp.AFFILIATION_CONTENT, cmd_content):
        aff_content = m.group("cnt")[1:-1].strip()
        aff_parts = cmd_util.split_ref_commands(r"\sup", aff_content)
        for aff_part in aff_parts:
            sup = regex.search(reg_exp.SUP_CONTENT, aff_part)
            if not sup:
                continue

            name = aff_content.replace(sup.group(0), "").strip()
            ref = sup.group("cnt")[1:-1].strip()
            affiliations.append({
                "name": cmd_util.sanitize(name),
                "ref_id": ref,
            })

    return cmd_util.join_author_and_affil_by_id(authors, affiliations)


def ext_single_aff(cmd_content: str, author_pattern: regex.Pattern[str], aff_pattern: regex.Pattern[str]) -> list[
    Author]:
    names_match = regex.search(author_pattern, cmd_content)
    aff_match = regex.search(aff_pattern, cmd_content)
    if not names_match or not aff_match:
        return []

    authornames = names_match.group("cnt")[1:-1].strip()
    affiliation = cmd_util.sanitize(aff_match.group("cnt")[1:-1])
    authors = reg_exp.split_on_separator(authornames)
    author_aff = []
    for author in authors:
        author = cmd_util.sanitize(author)
        author_aff.append(Author(author, [affiliation]))

    return author_aff


class AuthorNameAffiliation(SingleCmdScheme):
    r"""
    Author names are listed inside \authorname{} and each affiliations inside \affiliation{}. Affiliations can either
    be each in their own \affiliation{} or in the same one. Mostly \sup{} is used to refer to an affiliation, but if
    there is only one affiliation it is not used.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\authorname" in cmd_content and r"\affiliation" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.SUP_MULTI,
            lambda a, b: fr"\sup{{{a},{b}}}"
        )
        if r"\sup{" not in cmd_content and cmd_content.count(r"\affiliation{") == 1:
            # no refs used, all names share the same affiliation
            return ext_single_aff(cmd_content, reg_exp.AUTHORNAME_CONTENT, reg_exp.AFFILIATION_CONTENT)

        return _ext_multi_aff(cmd_content)
