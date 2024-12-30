import regex

from definition import latex
from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


class Institute(SingleCmdScheme):
    r"""
    Authors are separated by \and. Authors are followed by \institute{} for their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\institute" not in cmd_content:
            return False

        cmd_content = cmd_content[1:-1].strip()  # remove curly braces
        return bool(regex.fullmatch(reg_exp.VAL_AUTHOR_INSTITUTE_SEP_TEX_AND, cmd_content))

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = latex.remove_latex_newlines(cmd_content)
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.INSTITUTE_MULTI,
            lambda a, b: fr"\institute{{{a}, {b}}}"
        )

        author_aff = []
        for m in regex.finditer(reg_exp.EXT_AUTHOR_INSTITUTE_SEP_TEX_AND, cmd_content):
            name_part = m.group("name").strip()
            affiliation = cmd_util.sanitize(m.group("aff")[1:-1])
            names = reg_exp.split_on_separator(name_part)
            for name in names:
                author_aff.append(Author(cmd_util.sanitize(name), [affiliation]))

        return author_aff
