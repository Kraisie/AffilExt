import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util


class ArticleAuthors(SingleCmdScheme):
    r"""
    Using the \articleauthors{} command. This command houses multiple \author{} commands and each of those is
    followed by an \aff{} command for the affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        return cmd_name == "articleauthors"

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        author_aff = []
        for m in regex.finditer(reg_exp.EXT_ARTICLEAUTHORS_AUTHOR_AFF, cmd_content):
            name = cmd_util.sanitize(m.group("name")[1:-1])
            affiliation = cmd_util.sanitize(m.group("aff")[1:-1])
            author_aff.append(Author(name, [affiliation]))

        return author_aff
