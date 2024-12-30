import regex

from definition import reg_exp
from definition.data.Author import Author
from definition.data.SingleCmdScheme import SingleCmdScheme
from definition.single_cmd_scheme import cmd_util
from definition.single_cmd_scheme.compsocthanks import extract_compsoc_thanks


class Thanks(SingleCmdScheme):
    r"""
    Each author has a \thanks{} command for their affiliation.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\thanks" not in cmd_content:
            return False

        # replace all thanks commands with an empty one and check if each supposed author has a \thanks{}.
        # we need to replace the thanks content as it may include separators like ","
        cmd_content = regex.sub(reg_exp.THANKS_CONTENT, r"\\thanks{}", cmd_content)
        parts = reg_exp.split_on_separator(cmd_content)
        for part in parts:
            if r"\thanks{}" not in part:
                return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        text = cmd_content[1:-1]
        author_aff = []
        for m in regex.finditer(reg_exp.AUTHOR_THANKS_AFF, text):
            name = m.group("name")
            aff = m.group("aff")[1:-1]  # remove curly braces
            author_aff.append(Author(cmd_util.sanitize(name), [cmd_util.sanitize(aff)]))

        return author_aff


class ThanksMath(SingleCmdScheme):
    r"""
    The authors are listed first with a reference to their affiliation in math mode. The affiliations are each inside
    \thanks{} and contain the math mode reference.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\thanks" not in cmd_content:
            return False

        math_mode_refs = cmd_content.count("$^") + cmd_content.count("${}^")
        if math_mode_refs == 0:
            return False

        if bool(regex.search(reg_exp.PREDICATIVE_EXPRESSIONS, cmd_content)):
            return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        cmd_content = cmd_util.join_multi_cmd_occurrences(
            cmd_content, reg_exp.MATH_MODE_MULTI,
            lambda a, b: f"$^{{{a},{b}}}$"
        )

        affiliations = []
        for m in regex.finditer(reg_exp.THANKS_CONTENT, cmd_content):
            # replace thanks so in the end only names will be left over
            cmd_content = cmd_content.replace(m.group(0), "")
            content = m.group("cnt")
            for ref_match in regex.finditer(reg_exp.MATH_AFFILIATION, content):
                ref_id = ref_match.group("ref_id").strip("$^{}. ")
                name = ref_match.group("name")
                affiliations.append({
                    "name": name,
                    "ref_id": ref_id,
                })

        authors = []
        for m in regex.finditer(reg_exp.MATH_AUTHOR_REF, cmd_content):
            ref_id = m.group("ref_id").strip("$^{} ")
            ref_ids = cmd_util.split_ref_strings(ref_id)
            name = m.group("name")
            authors.append({
                "name": name,
                "ref_id": ref_ids,
            })

        return cmd_util.join_author_and_affil_by_id(authors, affiliations)


class ThanksWith(SingleCmdScheme):
    r"""
    The authors are listed first there is at least one \thanks{} after that. The content is structured like 'name(s)
    is/are with affiliation'.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\thanks" not in cmd_content:
            return False

        if r"\ieeecompsoc" in cmd_content or "authorblock" in cmd_content:
            return False

        # replace all thanks commands with an empty one and check if each supposed author has a \thanks{}.
        # we need to replace the thanks content as it may include separators like ","
        # check each thanks content for inclusion of a part like "is with"
        for m in regex.finditer(reg_exp.THANKS_CONTENT, cmd_content):
            content = m.group("cnt")[1:-1]
            if not bool(regex.search(reg_exp.PREDICATIVE_EXPRESSIONS, content)):
                return False

            cmd_content = cmd_content.replace(m.group(0), r"\\thanks{}")

        parts = reg_exp.split_on_separator(cmd_content)
        for part in parts:
            if r"\thanks{}" not in part:
                return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        text = cmd_content[1:-1]
        author_aff = []
        for m in regex.finditer(reg_exp.AUTHOR_THANKS_AFF, text):
            name = m.group("name")
            name = regex.sub(reg_exp.MATH_MODE_CONTENT, "", name)
            aff = m.group("aff")[1:-1]  # remove curly braces
            affiliation_parts = regex.split(reg_exp.PREDICATIVE_EXPRESSIONS, aff)
            if len(affiliation_parts) != 2:
                continue

            author_aff.append(Author(cmd_util.sanitize(name), [cmd_util.sanitize(affiliation_parts[1])]))

        return author_aff


class ThanksWithMath(SingleCmdScheme):
    r"""
    Basically similar to compsocthanks, but with \thanks{}.
    """

    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        cmd_content = cmd_content.lower()
        if r"\thanks" not in cmd_content:
            return False

        if r"\ieeecompsoc" in cmd_content or "authorblock" in cmd_content:
            return False

        return True

    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        # transform the command to a \ieeecompsocitemizethanks{} as they are practically the same
        cmd_content = regex.sub(reg_exp.MATH_MODE_CONTENT, "", cmd_content[1:-1].strip())
        compsoc_thanks = []
        for m in regex.finditer(reg_exp.THANKS_CONTENT, cmd_content):
            thanks_content = m.group("cnt")[1:-1].strip()
            compsoc_thanks.append(fr"\IEEEcompsocthanksitem {thanks_content}")
            cmd_content = cmd_content.replace(m.group(0), "")

        compsoc_cmd = fr"{{{cmd_content} \IEEEcompsocitemizethanks{{{' '.join(compsoc_thanks)}}}}}"
        return extract_compsoc_thanks(compsoc_cmd)
