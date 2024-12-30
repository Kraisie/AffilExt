import uuid

import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util

_DEFAULT_AFFILIATION = " French Institute for Research in Computer Science and Automation, France"


# replace thanks with a thanksref, to ensure not using the same ref-id on two different affiliations,
# uuid1 is used (based on host ID and time, no privacy issue as this will not be shared)
def _replace_thanks_with_ref(cmd: str) -> tuple[str, list[tuple[str, str]]]:
    affiliations = []
    ref_cmd = ""
    start = 0
    for m in regex.finditer(reg_exp.EXT_RRAUTHOR_THANKS_WITH_REF, cmd):
        thanks_content: str = m.group("cnt")[1:-1].strip()
        ref_id = m.group("ref_id") if m.group("ref_id") else str(uuid.uuid1())
        affiliations.append((ref_id, thanks_content))
        ref_cmd += cmd[start:m.start()]
        ref_cmd += fr" \thanksref{{{ref_id}}} "
        start = m.end()

    ref_cmd += cmd[start:]
    return ref_cmd, affiliations


def extract_with_substitute(cmd_content: str, sep: str, thanks=None) -> list[Author]:
    parts = cmd_content.split(sep)
    author_aff = []
    for part in parts:
        if not (m := regex.search(reg_exp.THANKS_CONTENT, part)):
            name = part
            affiliation = _DEFAULT_AFFILIATION
        else:
            name = part.replace(m.group(0), "")
            affiliation = m.group("cnt")[1:-1]
            if thanks:
                affiliation = next(a["thanks_content"] for a in thanks if a["thanks_id"] == affiliation)

        author_aff.append(Author(cmd_util.sanitize(name), [cmd_util.sanitize(affiliation)]))

    return author_aff


def _substitute_thanks_argument(cmd_content: str) -> tuple[str, list[dict]]:
    thanks = []
    substitute = ""
    start = 0
    for m in regex.finditer(reg_exp.THANKS_CONTENT, cmd_content):
        replacement = str(uuid.uuid1())
        thanks_content = m.group("cnt")[1:-1].strip()
        thanks.append({
            "thanks_id": replacement,
            "thanks_content": cmd_util.sanitize(thanks_content)
        })

        substitute += cmd_content[start:m.start()]
        substitute += fr" \thanks{{{replacement}}} "
        start = m.end()

    substitute += cmd_content[start:]
    return substitute, thanks


class RrAuthorThanks(SingleCmdScheme):
    r"""
    Uses the \RRauthor{} command, which seems to be from a package by 'French Institute for Research in Computer Science
    and Automation'. Authors are separated by comma or by \and. \thanks{} can be used to reference an affiliation.
    If no \thanks{} is used, the affiliation can be assumed as 'INRIA, France'.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return cmd_name == "rrauthor" and r"\thanks{" in cmd_content and r"\thanksref{" not in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        sep = r"\and " if r"\and " in cmd_content else ","
        # since there are probably commas in the thanks text we can not split on comma
        # so, we need to remove the text before doing anything else
        cmd_content, thanks = _substitute_thanks_argument(cmd_content) if sep == "," else (cmd_content, None)
        return extract_with_substitute(cmd_content, sep, thanks)


class RrAuthorThanksRef(SingleCmdScheme):
    r"""
    Uses the \RRauthor{} command, which seems to be from a package by 'French Institute for Research in Computer Science
    and Automation'. Authors are separated by comma or by \and. \thanks[]{} can be used to reference an affiliation the
    string inside [] is used as a reference. Any other author with the same affiliation can reference such an
    affiliation with \thanksref{}. If no \thanks{} is used, the affiliation can be assumed as 'INRIA, France'.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return cmd_name == "rrauthor" and r"\thanks[" in cmd_content and r"\thanksref{" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.THANKSREF_MULTI,
            lambda a, b: fr"\thanksref{{{a},{b}}}"
        )

        cmd_content = cmd_content[1:-1].strip()
        author_aff = []
        ref_cmd, affiliations = _replace_thanks_with_ref(cmd_content)
        sep = r"\and " if r"\and " in cmd_content else ","
        for part in ref_cmd.split(sep):
            if m := regex.search(reg_exp.THANKSREF_CONTENT, part):
                ref_id = m.group("cnt")[1:-1]
                name = cmd_util.sanitize(part.replace(m.group(0), ""))
                affiliation = next(a for a in affiliations if a[0] == ref_id)[1]
                author_aff.append(Author(name, [cmd_util.sanitize(affiliation)]))
            else:
                # part should be only the name now -> default to INRIA affiliation
                author_aff.append(Author(cmd_util.sanitize(part), [_DEFAULT_AFFILIATION]))

        return author_aff


class RrAuthorNoThanks(SingleCmdScheme):
    r"""
    Uses the \RRauthor{} command, which seems to be from a package by 'French Institute for Research in Computer Science
    and Automation'. Authors are separated by comma or by \and. Since no \thanks{} is used, the affiliation can be
    assumed as 'INRIA, France'.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return cmd_name == "rrauthor" and r"\thanks" not in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        names = reg_exp.split_on_separator(cmd_content)
        return [Author(cmd_util.sanitize(name), [_DEFAULT_AFFILIATION]) for name in names]
