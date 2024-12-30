import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _basic_affaddr_math_case(content: str) -> list[Author]:
    affiliations = []
    for m in regex.finditer(reg_exp.AFFADDR_CONTENT, content):
        affiliation = m.group("cnt")[1:-1]
        content = content.replace(m.group(0), "")
        ref_match = regex.search(reg_exp.MATH_MODE_CONTENT, affiliation)
        if not ref_match:
            continue

        ref_id = ref_match.group("cnt").strip("{}^ ")
        affiliations.append({
            "name": affiliation.replace(ref_match.group(0), ""),
            "ref_id": ref_id
        })

    authors = []
    content = content[13:] if content.startswith(r"\alignauthor ") else content
    for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, content):
        name = m.group("name")
        ref = m.group("ref_id")
        if not name or not ref:
            continue

        authors.append({
            "name": name,
            "ref_id": cmd_util.split_ref_strings(ref.strip("${}^ "))
        })

    return cmd_util.join_author_and_affil_by_id(authors, affiliations)


def _alignauthor_block(cmd_content: str) -> list[Author]:
    author_aff = []
    for m in regex.finditer(reg_exp.ALIGNAUTHOR_CONTENT, cmd_content):
        alignauthor_content = m.group("cnt")[1:-1]
        if "$" not in alignauthor_content and alignauthor_content.lower().count("affaddr") == 1:
            # sometimes if all authors share the same affiliation inside an \alignauthor{} block
            # there is no need for a reference.
            match = regex.search(reg_exp.AFFADDR_CONTENT, alignauthor_content)
            if not match:
                continue

            affiliation = match.group("cnt")[1:-1]
            rest = alignauthor_content[:match.start()] + alignauthor_content[match.end():]
            name_parts = [sname for name_line in rest.split(r"\\") if len(sname := name_line.strip()) > 0]
            for name_part in name_parts:
                names = reg_exp.split_on_separator(name_part)
                author_aff += [Author(cmd_util.sanitize(name), [cmd_util.sanitize(affiliation)]) for name in names]
        else:
            author_aff += _basic_affaddr_math_case(alignauthor_content)

    return author_aff


# ex (https://arxiv.org/src/2106.01399):
# \author{
#     J. Walker Orr\\
#     \affaddr{George Fox University}\\ \and
#     Nathaniel Russell\\
#     \affaddr{George Fox University}\\
# }
def _ordered(parts: list[str]) -> list[Author]:
    names = []
    affiliations = []
    author_affs = []
    for part in parts:
        if part.lower().startswith(r"\affaddr"):
            # same as with _affaddr_block()
            affiliations.append(cmd_util.sanitize(part[8:]))
        else:
            if len(names) > 0 and len(affiliations) > 0:
                for name in names:
                    author_affs.append(Author(name, affiliations))
                affiliations = []
                names = []

            names += [cmd_util.sanitize(name) for name in reg_exp.split_on_separator(part)]

    author_affs += [Author(name, affiliations) for name in names]
    return author_affs


# two cases:
# - all authors have the same multiple affiliations (no example found)
# - the affiliation is split into parts, e.g.
#       https://arxiv.org/src/1504.07558
#       \author{
#           Marco Autili, Vittorio Cortellessa, Paolo Di Benedetto, Paola Inverardi\\ \\
#           \affaddr{Dipartimento di Informatica }\\
#           \affaddr{Universit di L'Aquila}\\
#           \affaddr{via Vetoio 1, L'Aquila, ITALY }\\
#       }
# since there is no way for us to know which case this is, we join all affiliation parts
def _affaddr_block(parts: list[str]) -> list[Author]:
    name_parts = []
    affiliation_parts = []
    for part in parts:
        if part.lower().startswith(r"\affaddr"):
            # not using regex here as not everyone encapsulates cmd argument in curly braces
            # e.g.: "\affaddr name" instead of "\affaddr{name}"
            aff = part[8:].strip("{} ")
            affiliation_parts.append(aff)
        else:
            name_parts += reg_exp.split_on_separator(part)

    affiliation = cmd_util.sanitize(", ".join(affiliation_parts))
    return [Author(cmd_util.sanitize(name), [affiliation]) for name in name_parts]


# after the last line of names there are only lines starting with \affaddr{}
def _has_affaddr_block(parts: list[str]) -> bool:
    if len(parts) < 3:
        return False

    started_affaddr_part = False
    for part in parts[1:]:
        part = part.lower()
        if part.startswith(r"\affaddr"):
            started_affaddr_part = True
        elif started_affaddr_part:
            # line is not starting with \affaddr{}, but we already encountered one of those, thus this is not a
            # block of \affaddr{}
            return False

    return True


def _single_aff(parts: list[str]) -> list[Author]:
    authors = reg_exp.split_on_separator(parts[0])
    affiliation = parts[1]
    m = regex.search(reg_exp.AFFADDR_CONTENT, affiliation)
    if not m:
        return []

    content = cmd_util.sanitize(m.group("cnt")[1:-1])
    return [Author(cmd_util.sanitize(author), [content]) for author in authors]


def _ext_authors(cmd_content: str) -> list[dict]:
    authors = []
    for m in regex.finditer(reg_exp.AFFMARK_AUTHOR, cmd_content):
        name = m.group("name").strip(r"{},\ ")
        ref = m.group("ref").strip()
        ref_ids = cmd_util.split_ref_strings(ref)
        authors.append({
            "name": name,
            "ref_id": ref_ids
        })

    return authors


def _ext_affiliations(text: str) -> dict:
    match = regex.search(reg_exp.AFFMARK_CONTENT, text)
    ref = match.group("cnt")[1:-1].strip() if match else ""
    name = text.replace(match.group(0), "")  # should only leave name of affiliation

    return {
        "name": name.strip(r"{},\ "),
        "ref_id": ref
    }


class AlignAuthorAffAddr(SingleCmdScheme):
    r"""
    Each author is preceded by \alignauthor and the following \affaddr{} contains the affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\alignauthor" in cmd_content and r"\affaddr" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        author_aff = []
        parts = [spart for part in cmd_content[1:-1].split(r"\alignauthor") if len(spart := part.strip()) > 0]
        for part in parts:
            affiliation_parts = []
            for m in regex.finditer(reg_exp.AFFADDR_CONTENT, part):
                content = m.group("cnt")[1:-1].strip()
                part = part.replace(m.group(0), "")
                if content:
                    affiliation_parts.append(content)

            affiliation = cmd_util.sanitize(", ".join(affiliation_parts))
            name_parts = [sname_part for name_part in part.split(r"\\") if len(sname_part := name_part.strip()) > 0]
            for name_part in name_parts:
                names = reg_exp.split_on_separator(name_part)
                for name in names:
                    author_aff.append(Author(cmd_util.sanitize(name), [affiliation]))

        return author_aff


class AffMarkAffAddr(SingleCmdScheme):
    r"""
    Each author is followed by \affmark{} with a reference to an affiliation.
    Each affiliation is inside \affaddr{} is preceded by \affmark{} with its reference.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()

        # check that each affaddr has an affmark
        for m in regex.finditer(reg_exp.AFFADDR_CONTENT, cmd_content):
            if r"\affmark" not in m.group(0):
                return False

        return r"\affmark" in cmd_content and r"\affaddr" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AFFMARK_MULTI,
            lambda a, b: fr"\affmark[{a},{b}]"
        )
        affiliations = []
        for m in regex.finditer(reg_exp.AFFADDR_CONTENT, cmd_content):
            content = m.group("cnt")[1:-1].strip()
            if r"\affaddr" in content.lower():
                # some wrap affaddr in affaddr: \affaddr{\affaddr{}, \affaddr{}}
                for wm in regex.finditer(reg_exp.AFFADDR_CONTENT, content):
                    affiliations.append(_ext_affiliations(wm.group("cnt")[1:-1].strip()))
                    cmd_content = cmd_content.replace(wm.group(0), "")
            else:
                affiliations.append(_ext_affiliations(content))
                cmd_content = cmd_content.replace(m.group(0), "")  # remove affiliation occurrence to only leave names

        authors = _ext_authors(cmd_content)
        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class AffMarkNoAffAddr(SingleCmdScheme):
    r"""
    Each author is followed by \affmark{} with a reference to an affiliation.
    Each affiliation is preceded by \affmark{} with its reference but is not inside a \affaddr{}.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\affmark" in cmd_content and r"\affaddr" not in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AFFMARK_MULTI,
            lambda a, b: fr"\affmark[{a},{b}]"
        )
        affiliations = []
        authors = []
        for line in cmd_content.split(r"\\"):
            line = line.strip()
            if line.startswith(r"\affmark"):
                affiliations.append(_ext_affiliations(line))
            else:
                authors += _ext_authors(line)

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class AffAddr(SingleCmdScheme):
    r"""
    The affiliation is inside a \affaddr{} but the authors are just text.
    There are different ways to assign an author to an affiliation. See implementation for details.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\affmark" in cmd_content or r"\alignauthor" in cmd_content:
            return False

        return r"\affaddr" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].rstrip()
        parts = [spart for part in cmd_content.split(r"\\") if len(spart := part.strip()) > 0]
        if len(parts) == 0:
            return []

        if len(parts) == 2:
            # [names, aff]
            return _single_aff(parts)

        if _has_affaddr_block(parts):
            # list of names is followed by multiple \affaddr{}
            return _affaddr_block(parts)

        # assume that the list is ordered like [name, aff, name, aff, name, aff]
        return _ordered(parts)


class AffAddrMathMode(SingleCmdScheme):
    r"""
    The affiliation is inside a \affaddr{} but the authors are just text.
    There are references to affiliations in math mode.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\affaddr" not in cmd_content:
            return False

        if r"\affmark" in cmd_content:
            return False

        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs == 0:
            return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_content[1:-1].strip()
        cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )

        if r"\alignauthor{" in cmd_content:
            return _alignauthor_block(cmd_content)

        return _basic_affaddr_math_case(cmd_content)
