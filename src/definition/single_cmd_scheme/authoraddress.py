from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import authorname


class AuthorAddress(SingleCmdScheme):
    r"""
    Author names are listed inside \author{} and the affiliation inside \address{}.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        return r"\author{" in cmd_content and r"\address{" in cmd_content

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        return authorname.ext_single_aff(cmd_content, reg_exp.AUTHOR_CONTENT, reg_exp.ADDRESS_CONTENT)
