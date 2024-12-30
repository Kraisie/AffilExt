import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


def _match_name_with_affiliation(authors: list[str], name_part: str, affiliation_part: str) -> list[Author]:
    lower_sname = name_part.strip().lower()
    if lower_sname == "all authors" or lower_sname == "all the authors" or lower_sname == "authors":
        return [Author(cmd_util.sanitize(author), [cmd_util.sanitize(affiliation_part)]) for author in authors]

    author_affs = []
    lower_name_part = name_part.lower()
    for author in authors:
        if author.lower() in lower_name_part:
            author_affs.append(Author(cmd_util.sanitize(author), [cmd_util.sanitize(affiliation_part)]))
            continue

        # while short names are used most of the time, they do not adhere to a standard formatting.
        # "Alfa Bravo Charlie" -> "A. Charlie", "A. B. Charlie", "B. Charlie"
        # "Alfa-Bravo Charlie" -> "A. Charlie", "A.-B. Charlie", "A. B. Charlie", "AB. Charlie", "B. Charlie"
        # "Alfa Bravo-Charlie" -> "A. Bravo-Charlie", "A. Bravo Charlie"
        # thus, we only check for the last name. to make sure it is not part of a word we add spaces to the start but,
        # not to the end as that would be out of bounds for lower_name_part anyway.
        # this will lead to issues if multiple authors have the same last name but different affiliations.
        last_name = f" {author.split(" ")[-1]}".lower()
        if last_name in lower_name_part or last_name.replace("-", " ") in lower_name_part:
            author_affs.append(Author(cmd_util.sanitize(author), [cmd_util.sanitize(affiliation_part)]))
            continue

        # if the name did not appear in full or as last name it might be referenced with "the other authors"
        if "the other authors" in lower_name_part:
            author_affs.append(Author(cmd_util.sanitize(author), [cmd_util.sanitize(affiliation_part)]))

    return author_affs


def _split_name_and_affiliation(affiliation: str) -> list[tuple[str, str]]:
    parts = regex.split(reg_exp.PREDICATIVE_EXPRESSIONS, affiliation)
    if len(parts) < 2:
        return []

    # normally the parts will be "name1, name2, name3" and "affiliation". however, sometimes there are multiple
    # sentences like "name is with aff1. he is also with aff2". Then we will have the following parts:
    # ["name", "aff1. he", "aff2"]
    # There are the following structures:
    # - Multiple authors in the same \IEEEcompsocthanksitem (name1 is with aff1. name2 is with aff2)
    # - Multiple affiliations for the same author (name is with aff1. he is also with aff2)
    # - Former affiliations of an author (name is with aff1. part of this work was done while at aff2)
    # - some combination of the above
    # 15% of the papers (of the dataset used for developing) that use the compocthanks fit into those categories, that
    # means 0.2% of the total papers. thus, we just skip these.
    if len(parts) > 2:
        return []

    return [(parts[0].strip(), parts[1].strip())]


def _join_thanks(cmd_content: str) -> str:
    thanks = []
    start = -1
    end = -1
    for m in regex.finditer(reg_exp.COMP_SOC_ITEMIZE_CONTENT, cmd_content):
        if start == -1:
            start = m.start()

        thanks.append(m.group("cnt")[1:-1].strip())
        end = m.end()

    return fr"{cmd_content[:start]} \IEEEcompsocitemizethanks{{{' '.join(thanks)}}} {cmd_content[end:]}"


def extract_compsoc_thanks(cmd_content: str) -> list[Author]:
    cmd_content = _join_thanks(cmd_content)
    itemize_match = regex.search(reg_exp.COMP_SOC_ITEMIZE_CONTENT, cmd_content)
    if not itemize_match:
        return []

    full_match = itemize_match.group(0)
    names = cmd_util.sanitize(cmd_content.replace(full_match, ""))  # avoid stuff like \thanks{} in names
    authors = reg_exp.split_on_separator(names)
    itemize_content = itemize_match.group("cnt")[1:-1].strip()
    affiliations = [spart for part in itemize_content.split(r"\IEEEcompsocthanksitem") if
                    len(spart := part.strip()) > 0]

    author_affs = []
    for affiliation_part in affiliations:
        names_and_aff_parts = _split_name_and_affiliation(affiliation_part)
        for name, affiliation in names_and_aff_parts:
            name = cmd_util.sanitize(name)  # replace any thanks{} or other latex elements
            author_affs += _match_name_with_affiliation(authors, name, affiliation)

    return author_affs


class CompSocItemizeThanks(SingleCmdScheme):
    r"""
    Author names are listed first. The affiliations are inside an \IEEEcompsocitemizethanks{} as
    \IEEEcompsocthanksitem and follow the structure of 'name(s) is/are with affiliation'
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        return r"\IEEEcompsocitemizethanks" in cmd_content and r"\IEEEcompsocthanksitem" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        return extract_compsoc_thanks(cmd_content)
