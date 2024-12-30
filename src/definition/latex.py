import logging

import regex

from definition import reg_exp

_logger = logging.getLogger(__name__)

_OTHER_COMMANDS = [
    "footnote",
    "institute",
    "thanks"
]


def _remove_orcid_ids(text: str) -> str:
    text = regex.sub(reg_exp.LATEX_ORCID_CMDS, "", text)
    text = regex.sub(reg_exp.LATEX_PLAIN_ORCID_ID, "", text)
    text = regex.sub(reg_exp.LATEX_HREF_ORCID_ID, "", text)
    text = regex.sub(reg_exp.LATEX_URL_ORCID_ID, "", text)
    return text



def _get_closest_previous_footnote(text: str) -> str:
    m = regex.search(reg_exp.FOOTNOTE_CONTENT_REVERSE, text)  # start at the end
    if not m:
        return ""  # results in removing the fnmark

    return m.group(0)


def _get_other_commands(cmd_content: str) -> list[str]:
    cmds = []
    for m in regex.finditer(reg_exp.LATEX_FULL_COMMAND, cmd_content, overlapped=True):  # also find cmds in cmds
        cmd_name = m.group("name")
        if cmd_name in _OTHER_COMMANDS:
            cmds.append(m.group(0))

    return cmds


# footnotemarks reference another footnote that other commands might produce.
# to properly handle them, we need to replace the marks with the command they reference.
# this procedure is not perfect as
# - previous commands outside the extracted cmds could have affected the counter
# - it is also possible to modify those counters with commands like \addtocounter{footnote}{n} or
#   \setcounter{footnote}{n} with n being some integer
# however, since the author commands commonly appear pretty early in a tex document, the chances are good to find the
# matching reference
def _replace_fnmarks_with_reference(latex: str) -> str:
    if r"\footnotemark" not in latex:
        return latex

    cmds = _get_other_commands(latex)
    if len(cmds) == 0:
        return latex

    for m in regex.finditer(reg_exp.FOOTNOTEMARK_CONTENT, latex):
        fn_mark = m.group("cnt")[1:-1].strip()
        if not fn_mark or fn_mark.lower() == r"\value{footnote}":
            reference = _get_closest_previous_footnote(latex[:m.start()])
        elif fn_mark.isdigit():
            index = int(fn_mark) - 1  # latex index starts at 1
            reference = cmds[index] if 0 <= index < len(cmds) else ""  # remove fnmark when no reference found
        else:
            _logger.warning("Unhandled case for footnotemark content: '%s' in '%s'", fn_mark, latex)
            continue

        latex = latex[:m.start()] + reference + latex[m.end():]

    return latex


def _replace_escaped_chars(latex: str) -> str:
    return regex.sub(reg_exp.LATEX_ESCAPED_CHARS, r"\g<char>", latex)  # replace match with group("char")

def _tex_diacritics_to_unicode(combining_char, char) -> str | None:
    # "Older versions of LaTeX would not remove the dot on top of the i and j letters when adding a diacritic.
    # To correct this, one had to use the dotless version of these letters, by typing \i and \j."
    # - https://en.wikibooks.org/wiki/LaTeX/Special_Characters
    if char == r"\i" and combining_char:
        char = "ı"

    if char == r"\j" and combining_char:
        char = "ȷ"

    if not char:
        match combining_char:
            # @formatter:off
            case "l": return "ł"
            case "L": return "Ł"
            case "o": return "ø"
            case "O": return "Ø"
            # @formatter:on
            case _:
                _logger.warning("Unknown combining character '%s'.", combining_char, char)
                return None

    # Table 5: https://tug.ctan.org/info/symbols/comprehensive/symbols-a4.pdf
    if not combining_char:
        match char:
            # @formatter:off
            case "i": return "ı"
            case "j": return "ȷ"
            case "l": return "ł"
            case "L": return "Ł"
            case "o": return "ø"
            case "O": return "Ø"
            case "aa": return "å"
            case "AA": return "Å"
            case "ae": return "æ"
            case "AE": return "Æ"
            case "dh": return "ð"
            case "dj": return "đ"
            case "DJ" | "DH": return "Đ"
            case "ij": return "ĳ"
            case "IJ": return "Ĳ"
            case "ng": return "ŋ"
            case "NG": return "Ŋ"
            case "oe": return "œ"
            case "OE": return "Œ"
            case "ss": return "ß"
            case "SS": return "SS"  # no upper case :c
            case "th": return "þ"
            case "TH": return "Þ"
            # @formatter:on
            case _:
                # {\S} = § and {\P} = ¶ get used in affiliation references
                _logger.debug("Unknown combining character '%s' with char '%s'", combining_char, char)
                return None

    # Table 19: https://tug.ctan.org/info/symbols/comprehensive/symbols-a4.pdf
    match combining_char:
        # @formatter:off
        case "`": return f"{char}\u0300"  # grave
        case "'": return f"{char}\u0301"  # acute
        case "^": return f"{char}\u0302"  # circumflex
        case "~": return f"{char}\u0303"  # nasal vowel
        case "=": return f"{char}\u0304"  # macron
        case "u": return f"{char}\u0306"  # breve
        case ".": return f"{char}\u0307"  # dot above
        case '"': return f"{char}\u0308"  # umlaut, trema, dieresis
        case "h": return f"{char}\u0309"  # hook above
        case "r": return f"{char}\u030A"  # ring above
        case "H": return f"{char}\u030B"  # hungarian umlaut / double acute
        case "v": return f"{char}\u030C"  # caron
        case "|": return f"{char}\u030D"  # vertical line above
        case "U": return f"{char}\u030E"  # double vertical line above, different result with cyrillic font
        case "C": return f"{char}\u030F"  # double grave
        case "f": return f"{char}\u0311"  # inverted breve
        case "b": return f"{char}\u0320"  # bar below
        case "d": return f"{char}\u0323"  # dot below
        case "c": return f"{char}\u0327"  # cedilla
        case "k": return f"{char}\u0328"  # ogonek
        case "t": return f"{char}\u0361"  # tie
        # @formatter:on
        case _:
            _logger.warning("Unknown combining character '%s' with char '%s'", combining_char, char)
            return None


def _sub_csc(match: regex.Match[str]) -> str:
    combining_char = match.group("c_char")
    char = match.group("char")
    replacement = _tex_diacritics_to_unicode(combining_char, char)
    if not replacement:
        _logger.debug("Could not escape '%s'", match.group(0))
        return match.group(0)

    return replacement


def _replace_composite_special_chars(tex: str):
    return regex.sub(reg_exp.LATEX_SPECIAL_CHARS_DIACRITIC, _sub_csc, tex)


def _find_comment_index(line: str) -> int:
    start = 0
    while (comment_index := line.find("%", start)) != -1:
        if line[comment_index - 1] == "\\":
            # could be \\% or \%, first one is newline and comment, second is an escaped percent
            if line[comment_index - 2] == "\\":
                return comment_index
        else:
            return comment_index

        start = comment_index + 1
    return -1


def remove_comments(tex: str) -> str:
    nc_tex = ""
    for line in tex.splitlines(keepends=True):  # keep the linebreaks
        if line.strip() == "" or line.lstrip().startswith("%"):
            continue

        comment_start = _find_comment_index(line)
        nc_tex += f"{line[:comment_start].rstrip()}\n" if comment_start != -1 else line

    nc_tex = regex.sub(reg_exp.LATEX_COMMENT_BLOCK, "", nc_tex)
    return nc_tex


def _remove_multi_space(tex: str) -> str:
    return regex.sub(reg_exp.SPACE_MULTI, " ", tex).strip()  # multiple line breaks and multiple spaces


def remove_latex_newlines(tex: str) -> str:
    # \\ are sometimes used for separation, however, mostly for formatting. some extraction methods
    # might not need \\ for anything and would rather have an easily matchable whitespace instead
    tex = tex.replace(r"\newline", " ")
    tex = tex.replace(r"\\", " ")
    return _remove_multi_space(tex)


def _remove_tex_spacing(tex: str) -> str:
    tex = tex.replace("~", " ")
    tex = tex.replace(r"\newline", "\\\\")
    tex = regex.sub(reg_exp.LATEX_SPACING, " ", tex)
    return tex


def _unwrap_fonts_in_text(latex: str) -> str:
    unwrapped = ""
    start = 0
    for m in regex.finditer(reg_exp.LATEX_STYLES, latex):
        style_start = m.start()
        part = latex[style_start:]
        cnt_match = regex.search(reg_exp.NESTED_CONTENT_IN_CURLY, part)  # should start at start of m
        content = cnt_match.group(0)[len(m.group(0)):-1]  # -1 to remove the last curly brace
        unwrapped += latex[start:style_start] + content
        start = style_start + cnt_match.end()

    unwrapped += latex[start:]
    return unwrapped


def _sub_fonts_in_cmds(match: regex.Match[str]) -> str:
    cmd_name = match.group("name")
    cmd_opt_args = match.group("opt_args") if match.group("opt_args") else ""
    args = []
    for i in range(1, 4):
        group_name = f"cnt{i}"
        arg = match.group(group_name)
        if not arg:
            break

        arg_content = _unwrap_fonts_in_cmds(arg[1:-1].strip())
        if n := regex.search(reg_exp.LATEX_STYLES_START, arg_content):
            arg_content = arg_content[len(n.group(0)):].strip()

        args.append(arg_content)

    args_str = ""
    for arg in args:
        args_str += f"{{{arg}}}"

    return fr" \{cmd_name}{cmd_opt_args}{args_str} "


def _unwrap_fonts_in_cmds(latex: str) -> str:
    return regex.sub(reg_exp.LATEX_FULL_COMMAND, _sub_fonts_in_cmds, latex)


def _unwrap_fonts(latex: str) -> str:
    # we need to unwrap fonts in command content first to avoid having stuff like "\author{\rm ...}" unwrapped to
    # "\author...". to do that we need to only remove the font command inside the command content, no braces.
    # however, for occurrences in text we need to remove the braces so "{\rm forename surname}" does not turn
    # into "{forename surname}" but "forename surname". this requires the commands to be handled first as we need
    # to remove the curly braces. Lastly remove font commands that have no curly braces like
    # "normal text \rm roman text".
    latex = _unwrap_fonts_in_cmds(latex)
    latex = _unwrap_fonts_in_text(latex)
    latex = regex.sub(reg_exp.LATEX_STYLES_NO_CURLY, "", latex)
    return latex


def _sub_unwrap_parbox(match: regex.Match[str]) -> str:
    content = match.group("cnt")
    return content[1:-1].strip() if content else ""


def sub_unwrap_cmds(match: regex.Match[str]) -> str:
    arg_one = match.group("cnt1")[1:-1]
    arg_two = match.group("cnt2")[1:-1] if match.group("cnt2") else ""  # 2nd arg is optional, most cmds only have one
    arg_three = match.group("cnt3")[1:-1] if match.group("cnt3") else ""  # 3rd arg is optional, even rarer than two
    return f" {' '.join([arg for arg in [arg_one, arg_two, arg_three] if arg])} "


def _unwrap_cmds(latex: str) -> str:
    # use a while loop to handle overlapping matches (outer to inner)
    # overlapped flag only exists for findall and finditer, not for sub, which makes it annoying
    while m := regex.search(reg_exp.LATEX_CMDS_TO_UNWRAP, latex):
        latex = latex[:m.start()] + sub_unwrap_cmds(m) + latex[m.end():]

    # unwrap parbox
    return regex.sub(reg_exp.PARBOX_CONTENT, _sub_unwrap_parbox, latex)


def sanitize_latex_cmd(latex: str) -> str:
    # unwrap specific commands
    latex = _unwrap_cmds(latex)
    latex = _unwrap_fonts(latex)  # needs to happen after unwrapping cmds
    # remove useless commands
    latex = regex.sub(reg_exp.LATEX_USELESS_CMDS_NO_ARGS, "", latex)
    latex = regex.sub(reg_exp.LATEX_USELESS_CMDS, "", latex)
    latex = regex.sub(reg_exp.LATEX_USELESS_EMAIL, "", latex)
    latex = regex.sub(reg_exp.LATEX_DESCRIPTORS, "", latex)
    # remove special latex spacing and characters
    latex = _remove_tex_spacing(latex)
    latex = _replace_composite_special_chars(latex)
    latex = _replace_escaped_chars(latex)
    latex = regex.sub(reg_exp.LATEX_MEASUREMENTS, "", latex)
    # replace fnmarks with their reference (if known)
    latex = _replace_fnmarks_with_reference(latex)
    latex = _remove_orcid_ids(latex)
    # remove any resulting repetition of whitespaces
    return _remove_multi_space(latex)
