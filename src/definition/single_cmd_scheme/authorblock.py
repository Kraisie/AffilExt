import regex

from definition import latex
from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _find_affiliations(block: str) -> list[dict]:
    affiliations = []
    for m in regex.finditer(reg_exp.MATH_AFFILIATION, block):
        ref_id = m.group("ref_id").strip("$^{} ")
        name = m.group("name")
        affiliations.append({
            "name": name,
            "ref_id": ref_id,
        })

    return affiliations


def _find_authors(block: str) -> list[dict]:
    authors = []
    for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, block):
        name = m.group("name").strip(", ")
        ref = m.group("ref_id").strip("$^{} ")
        if not name or not ref:
            continue

        ref_ids = cmd_util.split_ref_strings(ref)
        authors.append({
            "name": name,
            "ref_id": ref_ids
        })

    return authors


def _get_affiliation_refs_from_block(block: str) -> list[dict]:
    affiliations = []
    for m in regex.finditer(reg_exp.EXT_AUTHORBLOCK_REF_AFFILIATION, block):
        name = m.group("name")
        ref_id: str = m.group("ref_id")[1:-1]
        affiliations.append({
            "name": name.strip(),
            "ref_id": ref_id.strip()
        })

    return affiliations


def _get_author_refs_from_block(block: str) -> list[dict]:
    authors = []
    for m in regex.finditer(reg_exp.EXT_AUTHORBLOCK_REF_AUTHOR, block):
        name = m.group("name")
        ref_ids = [r.strip() for r in m.group("ref_id")[1:-1].split(",")]
        authors.append({
            "name": name.strip(),
            "ref_id": ref_ids
        })

    return authors


def _get_authorblocks(text: str) -> list[dict]:
    blocks = []
    for m in regex.finditer(reg_exp.EXT_AUTHORBLOCK_BLOCKS, text):
        blocks.append({
            "type": "name" if m.group("block_type").lower() == "n" else "aff",
            "content": m.group("block_content")[1:-1].strip()
        })

    return blocks


class AuthorBlock(SingleCmdScheme):
    r"""
    Each author name is inside an \authorblockN{}.
    After each author name there is an \authorblockA{} for their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        lower_cmd_content = cmd_content.lower()
        return "authorblockn" in lower_cmd_content and "authorblocka" in lower_cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        # there might be multiple authorblockA behind each other, mostly used for emails
        # however, sometimes both contain some part of the affiliation
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AUTHORBLOCKA_MULTI,
            lambda a, b: fr"\authorblockA{{{a}, {b}}}"
        )

        # mostly people that share the same affiliation
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AUTHORBLOCKN_MULTI,
            lambda a, b: fr"\authorblockN{{{a}, {b}}}"
        )

        blocks = _get_authorblocks(cmd_content)
        affiliation = ""
        authors = []
        author_aff = []
        for block in blocks:
            if block["type"] == "aff":
                affiliation = cmd_util.sanitize(block["content"])
            else:
                # encountered a name with already having an affiliation which means we encountered a new section.
                # thus, save the old section and clear the affiliation
                if affiliation:
                    for author in authors:
                        author_aff.append(Author(cmd_util.sanitize(author), [affiliation]))

                    affiliation = ""

                authors = reg_exp.split_on_separator(block["content"])

        if affiliation and len(authors) > 0:
            for author in authors:
                author_aff.append(Author(cmd_util.sanitize(author), [affiliation]))

        return author_aff


class AuthorBlockWithRef(SingleCmdScheme):
    r"""
    Each author name is inside an \authorblockN{}. Each affiliation is inside an \authorblockA{}.
    After each author name there is an \authorrefmark{} as a reference to their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        lower_cmd_content = cmd_content.lower()
        if ("authorblockn" not in lower_cmd_content or "authorblocka" not in lower_cmd_content or
                "authorrefmark" not in lower_cmd_content):
            return False

        blocks = _get_authorblocks(lower_cmd_content)
        last_block = blocks[-1]
        end = len(blocks)
        if last_block["type"] == "name" and "@" in last_block["content"] and "authorrefmark" not in last_block[
            "content"]:
            end -= 1  # ignore the last block with emails inside

        # check that there is an authorrefmark in each block
        for block in blocks[:end]:
            if "authorrefmark" not in block["content"]:
                return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = latex.remove_latex_newlines(cmd_content)
        # authorrefmark can appear as \authorrefmark{1,2} or \authorrefmark{1}\authorrefmark{2}
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.AUTHOR_REF_MARK_MULTI,
            lambda a, b: fr"\authorrefmark{{{a},{b}}}"
        )
        blocks = _get_authorblocks(cmd_content)
        authors = []
        affiliations = []
        for block in blocks:
            block_content = block["content"]
            if block["type"] == "name":
                authors += _get_author_refs_from_block(block_content)
            else:
                affiliations += _get_affiliation_refs_from_block(block_content)

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class AuthorBlockMath(SingleCmdScheme):
    r"""
    The authors are either in multiple \authorblockN{}, or in the same one. Same applies to the affiliations.
    The connection between author and affiliation gets made by an identifier in math mode.
    That identifier mostly appears right of an author name and left of an affiliation name.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs == 0:
            return False

        lower_cmd_content = cmd_content.lower()
        if "authorblockn" not in lower_cmd_content or "authorblocka" not in lower_cmd_content:
            return False

        if "authorrefmark" in lower_cmd_content:
            return False

        # check that math mode gets used in each block
        blocks = _get_authorblocks(cmd_content)
        for block in blocks:
            if "$" not in block["content"]:
                return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        blocks = _get_authorblocks(cmd_content)
        authors = []
        affiliations = []
        for block in blocks:
            if block["type"] == "name":
                block_content = cmd_util.join_multi_cmd_occurrences(
                    block["content"], reg_exp.MATH_MODE_MULTI,
                    lambda a, b: f"$^{{{a},{b}}}$"
                )
                authors += _find_authors(block_content)
            else:
                affiliations += _find_affiliations(block["content"])

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)
