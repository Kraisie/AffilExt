import regex

from definition import reg_exp
from definition.data.Author import Author


# find all indices (start position in a string) of a given search term
def find_all_indices(search_term: str, text: str):
    if not search_term or not text:
        return []

    indices = []
    pos = 0
    text = text.lower()
    search_term = search_term.lower()
    while (pos := text.find(search_term, pos)) != -1:
        indices.append(pos)
        pos += len(search_term)
    return indices


# join authors and their affiliations by matching references
def join_author_and_affil_by_id(authors: list[dict], affiliations: list[dict]) -> list[Author]:
    author_aff = []
    for author in authors:
        affs = []
        for affiliation in affiliations:
            sanitized_name = sanitize(affiliation["name"])
            if len(sanitized_name) == 0:
                # sometimes use references to their email which sanitize() removes to the sanitized_name is
                # an empty string. if that happens we do not need to save the affiliation
                continue

            if affiliation["ref_id"] in author["ref_id"]:
                affs.append(sanitized_name)

        author_aff.append(Author(sanitize(author["name"]), affs))

    return author_aff


# join two commands to a single one
def join_multi_cmd_occurrences(text: str, pattern: regex.Pattern[str], repl_func: callable):
    while m := regex.search(pattern, text):
        first = m.group("first").strip(r"{}\^ ")
        second = m.group("second").strip(r"{}\^ ")
        repl = repl_func(first, second)
        text = text[:m.start()] + repl + text[m.end():]
    return text


# split a string of affiliation references based on the used command, e.g.:
# "\cmd{ref1} aff1 \cmd{ref2} aff2" -> ["\cmd{ref1} aff1", "\cmd{ref2} aff2]
def split_ref_commands(command: str, text: str) -> list[str]:
    command_indices = find_all_indices(command, text)
    command_indices.append(len(text))  # add end of str so we always have start and end (no -1 as slicing is exclusive)
    return [text[start:end].strip() for start, end in zip(command_indices[:-1], command_indices[1:])]


def split_on_commands(commands: list[str], text: str) -> list[str]:
    parts = [text]
    for command in commands:
        new_parts = []
        for part in parts:
            indices = [0] + find_all_indices(command, part) + [len(part)]  # add start and end to keep whole content
            new_parts += [spart for s, e in zip(indices[:-1], indices[1:]) if len(spart := part[s:e].strip()) > 0]
        parts = new_parts

    return parts


def split_ref_strings(ref: str) -> list[str]:
    if len(ref) == 1:
        return [ref]

    if "," in ref:
        return [sref for r in ref.split(",") if len(sref := r.strip()) > 0]

    if "$" in ref:
        # this is not a normal math mode reference like "${}^1$"
        # $ will only be inside ref if there is a reference based on some command that uses math mode in its argument:
        # \cmd{$a$} and even \cmd{$a$$b$}
        # thus, we need to keep the $ for the matching between authors and affiliations
        return [m.group(0) for m in regex.finditer(reg_exp.MATH_MODE_CONTENT, ref)]

    if ref.count("\\") > 0:
        commands = split_ref_commands("\\", ref)
        ref_length = sum([len(cmd) for cmd in commands])
        if ref_length == len(ref.replace(" ", "")):
            # ref consists only of commands
            return commands

        # there is something else besides the commands that might be a reference
        rest = ref
        for cmd in commands:
            rest = rest.replace(cmd, "")

        return split_ref_strings(rest.strip()) + commands

    if " " in ref:
        return [sref for r in ref.split(" ") if len(sref := r.strip()) > 0]

    if "*" in ref:  # e.g.: "1*" which would be "1,*"
        return ["*"] + split_ref_strings(ref.replace("*", ""))

    return [ref]


def _remove_leftover_latex_special_chars(text: str) -> str:
    text = text.replace("$", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    text = text.replace("[", "")
    text = text.replace("]", "")
    text = text.replace("^", "")
    text = text.replace("\\", "")
    return text


def _remove_separators(text: str) -> str:
    text = regex.sub(reg_exp.LATEX_SEPARATORS_CMDS_ONLY, "", text.strip(", ")).strip()
    text = text[4:] if text.lower().startswith("and ") else text
    text = text[:-4] if text.lower().endswith(" and") else text
    return text


def _remove_leftover_commands(text: str) -> str:
    text = regex.sub(reg_exp.AUTHOR_CONTENT, r"\g<cnt>", text)
    text = regex.sub(reg_exp.INSTITUTION_CONTENT, r"\g<cnt>", text)

    text = regex.sub(reg_exp.INST_CONTENT, "", text)
    text = regex.sub(reg_exp.THANKS_CONTENT, "", text)
    text = regex.sub(reg_exp.FOOTNOTE_CONTENT, "", text)
    text = regex.sub(reg_exp.FOOTNOTEMARK_CONTENT, "", text)
    text = regex.sub(reg_exp.TITLENOTE_CONTENT, "", text)
    text = regex.sub(reg_exp.TEXTSUPERSCRIPT_CONTENT, "", text)
    return text


# this is meant to be used for author names and affiliations
def sanitize(text: str) -> str:
    text = _remove_separators(text)
    text = _remove_leftover_commands(text)
    text = regex.sub(reg_exp.LATEX_EMAIL, "", text)
    text = text.replace(r"\\", " ")  # remove latex newline
    text = _remove_leftover_latex_special_chars(text)
    text = text.strip(r",.;: ")  # remove punctuation at the start and end
    text = regex.sub(reg_exp.SPACE_MULTI, " ", text)
    return text.strip()


def get_cmd_content(cmd: str) -> str:
    # due to commands like \cmd{}{} we need to look for multiple, non-overlapping groups as cmd content
    content = ""
    for m in regex.finditer(reg_exp.NESTED_CONTENT_IN_CURLY, cmd):
        content += m.group(0).strip()

    return content


def get_cmd_name(cmd: str) -> str:
    b = cmd.find("[")
    c = cmd.find("{")
    end_index = b if b != -1 and b < c else c  # c has to exist -> c != -1 is always True
    return cmd[1:end_index].strip("* ")
