import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _find_affiliations(text: str) -> list[dict]:
    indices = cmd_util.find_all_indices(r"\inst{", text) + [len(text) - 1]  # append end of string as index
    affiliations = []
    for start, end in zip(indices[:-1], indices[1:]):
        part = text[start:end]
        m = regex.search(reg_exp.INST_CONTENT, part)
        if not m:
            continue

        ref = m.group("cnt")[1:-1].strip()
        name = part.replace(m.group(0), "")
        affiliations.append({
            "name": name,
            "ref_id": ref
        })

    return affiliations


class NameAffil(SingleCmdScheme):
    r"""
    The author name is followed by \affil{} for their affiliation.
    Sometimes there are multiple authors followed by the same affiliation.
    """

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        author_aff = []
        if m := regex.search(reg_exp.NAME_CONTENT, cmd_content):
            # unwrap some cases where \name{} is used
            cmd_content = cmd_content[:m.start()] + m.group("cnt")[1:-1].strip() + cmd_content[m.end():]

        for m in regex.finditer(reg_exp.NAME_AFFIL, cmd_content):
            name_part = m.group("name").strip()
            aff = cmd_util.sanitize(m.group("aff")[1:-1])
            names = reg_exp.split_on_separator(name_part)  # some define multiple names instead of one
            for name in names:
                author_aff.append(Author(cmd_util.sanitize(name), [aff]))

        return author_aff

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\textsuperscript" in cmd_content or r"\inst" in cmd_content:
            return False

        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs != 0:
            return False

        return r"\affil" in cmd_content


class AffilRefInst(SingleCmdScheme):
    r"""
    The author name is followed by an \affil{} with a reference to an affiliation.
    The affiliations are defined after \inst{} which contain the reference of that affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\inst" in cmd_content and r"\affil" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AFFIL_MULTI,
            lambda a, b: fr"\affil{{{a},{b}}}"
        )

        authors = []
        for m in regex.finditer(reg_exp.NAME_AFFIL, cmd_content):
            name = m.group("name")
            ref = m.group("aff")[1:-1].strip()
            ref_ids = cmd_util.split_ref_strings(ref)
            authors.append({
                "name": name,
                "ref_id": ref_ids,
            })

        affiliations = _find_affiliations(cmd_content)
        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class AffilMath(SingleCmdScheme):
    r"""
    The author names are followed by a math mode referent for their affiliation.
    The affiliations are in \affil{} and also have a reference in math mode.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\textsuperscript" in cmd_content or r"\inst" in cmd_content:
            return False

        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs == 0:
            return False

        return r"\affil" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )

        affiliations = []
        for m in regex.finditer(reg_exp.AFFIL_CONTENT, cmd_content):
            content = m.group("cnt")[1:-1].strip()
            for n in regex.finditer(reg_exp.MATH_AFFILIATION, content):
                ref = n.group("ref_id").strip("$^{} ")
                name = n.group("name")
                affiliations.append({
                    "name": name,
                    "ref_id": ref,
                })

            cmd_content = cmd_content.replace(m.group(0), "")

        authors = []
        for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, cmd_content):
            ref = m.group("ref_id").strip("$^{} ")
            name = m.group("name")
            authors.append({
                "name": name,
                "ref_id": cmd_util.split_ref_strings(ref),
            })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
