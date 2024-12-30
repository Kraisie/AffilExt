import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


class NameAddr(SingleCmdScheme):
    r"""
    Names are either preceded by a \name or are contained inside \name{} and affiliations are preceded an \addr or
    contained in \addr{}. All names in front of an (or multiple) addr share that/those affiliation(s).
    name
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\address" in cmd_content:
            return False

        return r"\name" in cmd_content and r"\addr" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        parts = cmd_util.split_on_commands([r"\name", r"\addr"], cmd_content)
        authors = []
        affiliations = []
        author_aff = []
        for part in parts:
            if part.lower().startswith(r"\name"):
                if len(affiliations) > 0:
                    for author in authors:
                        author_aff.append(Author(author, affiliations))

                    authors = []
                    affiliations = []

                authors.append(cmd_util.sanitize(part[5:]))
            elif part.lower().startswith(r"\addr"):
                affiliations.append(cmd_util.sanitize(part[5:]))
            # else ignore -> only ignores the part before the first \name (mostly "")

        for author in authors:
            author_aff.append(Author(author, affiliations))

        return author_aff


class NameAddrTextSuperScript(SingleCmdScheme):
    r"""
    Names are either preceded by a \name or are contained inside \name{} and affiliations are preceded an \addr or
    contained in \addr{}. Names are followed by \textsuperscript{} with a reference to an affiliation. Affiliations
    are prefixed with \textsuperscript{} or \ts{} that contains its reference.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\address" in cmd_content:
            return False

        if not r"\textsuperscript" in cmd_content:
            return False

        return r"\name" in cmd_content and r"\addr" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.TEXTSUPERSCRIPT_MULTI,
            lambda a, b: fr"\textsuperscript{{{a},{b}}}"
        )

        parts = cmd_util.split_on_commands([r"\name", r"\addr"], cmd_content)
        authors = []
        affiliations = []
        for part in parts:
            if part.lower().startswith(r"\name"):
                m = regex.search(reg_exp.TEXTSUPERSCRIPT_CONTENT, part)
                if not m:
                    continue

                ref = m.group("cnt")[1:-1].strip()
                ref_ids = cmd_util.split_ref_strings(ref)
                names = reg_exp.split_on_separator(part[5:].replace(m.group(0), ""))
                for name in names:
                    authors.append({
                        "name": cmd_util.sanitize(name),
                        "ref_id": ref_ids,
                    })
            elif part.lower().startswith(r"\addr"):
                m = regex.search(reg_exp.TEXTSUPERSCRIPT_CONTENT, part)
                if not m:
                    continue

                ref = m.group("cnt")[1:-1].strip()
                affiliations.append({
                    "name": cmd_util.sanitize(part[5:].replace(m.group(0), "")),
                    "ref_id": ref,
                })
            # else ignore -> only ignores the part before the first \name (mostly "")

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
