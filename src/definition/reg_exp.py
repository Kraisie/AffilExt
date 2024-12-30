import regex

from definition.data.Trie import Trie

# pre-compiling the regexes only makes a performance difference if more than the size of cached regexes are used and
# not in a repeating order. it is unlikely that this src reaches that cache limit of 512
# see note at https://docs.python.org/3/library/re.html#re.compile

_AUTHOR_CMDS = [
    "addauthor",
    "additionalauthors",
    "aistatsauthor",
    "articleauthors",
    "auteur",
    "auteurs",
    "author",
    "authora",
    "authoranon",
    "authorb",
    "authorbio",
    "authorblockN",
    "authorc",
    "authord",
    "authore",
    "authorinfo",
    "authorlist",
    "authorname",
    "authors",
    "authorsn",
    "author*",
    "authoreightname",
    "authorfivename",
    "authorfourname",
    "authorninename",
    "authoronename",
    "authorsevenname",
    "authorsixname",
    "authortenname",
    "authorthreename",
    "authortwoname",
    "firstauthorname",
    "secondauthorname",
    "thirdauthorname",
    "fourthauthorname",
    "hpcaauthors",
    "icmlauthor",
    "ieeeauthorblockn",
    "longauthor",
    "maintitleauthorlist",
    "midlauthor",
    "mlsysauthor",
    "name",
    "neutrAuthorListBib",
    "oneauthor",
    "rrauthor",
    "sauthor",
    "setauthor",
    "setauthors",
    "sysmlauthor",
    "thanks",
    "thesisauthor",
    "trauthor",
    "twoauthors"
]
_AFFILIATION_CMDS = [
    "address",
    "additionalaffiliation",
    "affa",
    "affaddr",
    "affgrous",
    "affb",
    "affc",
    "affd",
    "affe",
    "affil",
    "affiliate",
    "affilOne",
    "affiliation",
    "affiliationa",
    "affiliationb",
    "affiliationc",
    "affiliations",
    "affrdc",
    "affzack",
    "aistatsaddress",
    "authoraaddr",
    "authoraddr",
    "authoraffiliation",
    "authorbaddr",
    "authorblockA",
    "authorcaddr",
    "authordaddr",
    "authoreaddr",
    "authoreightaffil",
    "authorfiveaffil",
    "authorfouraffil",
    "authornineaffil",
    "authoroneaffil",
    "authorsevenaffil",
    "authorsixaffil",
    "authortenaffil",
    "authorthreeaffil",
    "authortwoaffil",
    "hpcaaffiliation",
    "icmlaffiliation",
    "icmladdress",
    "ieeeauthorblocka",
    "inst",
    "institute",
    "institutes",
    "institution",
    "institutions",
    "longaddress",
    "lyxaddress",
    "mlsysaffiliation",
    "neutrAddress",
    "neutrDepartment",
    "neutrInstitution",
    "publishers",
    "setaffiliation",
    "sysmlaffiliation",
    "thesislocation",
    "trgroup"
]
_USELESS_TEX_CMDS_NO_ARGS = [
    "baselineskip",  # formatting
    "bigskip",  # formatting
    "centering",  # centers text
    "enspace",  # .5em
    "enskip",  # .5em
    "hskip",  # formatting
    "hfill",  # formatting
    "medskip",  # medium space
    "negthickspace",  # negative of thick space
    "protect",  # fragile commands
    "selectfont",  # use an updated font, normally after \fontsize{}{}
    "smallskip",  # formatting
    "space",  # formatting
    "xspace"  # formatting
]
_USELESS_TEX_CMDS = [
    "color",  # text color
    "corauthref",  # display author as corresponding author
    "corr",  # display author as corresponding author
    "corref",  # display author as corresponding author
    "date",  # used to display current date
    "email",  # email
    "fnref",  # "footnoteref": equal contribution, support/funds, email/corresponding author, other information
    "fontsize",  # set the font size
    "hspace",  # formatting
    "hspace*",  # formatting
    "ieeemembership",  # display membership status in IEEE
    "includegraphics",  # display an image
    "postcode",  # specify the post src of an affiliation
    "revised",  # for revisions
    "state",  # specify the state of an affiliation
    "street",  # specify the street address of an affiliation
    "streetaddress",  # specify the street address of an affiliation
    "strut",  # used to guarantee an element has a minimum height
    "textcolor",  # text color
    "url",  # mostly used for emails and links to affiliation website, sometimes orcid
    "vspace*",  # formatting
    "vspace",  # formatting
]
# src: https://www.overleaf.com/learn/latex/Font_sizes%2C_families%2C_and_styles#Reference_guide
# commands that are used in structures like {\cmd ...} to modify text inside the curly braces
_LATEX_STYLES = [
    # font sizes
    "tiny",
    "scriptsize",
    "footnotesize",
    "normalsize",
    "small",
    "large",
    "huge",
    # font styles
    "em",
    "emph",
    "rm",
    "sf",
    "tt",
    "it",
    "sl",
    "sc",
    "bf",
    "textbf",
    "textit",
    "textlf",
    "textmd",
    "textnormal",
    "textrm",
    "textsc",
    "textsf",
    "textsl",
    "texttt",
    "textup",
    "normalfont",
    "rmfamily",
    "sffamily",
    "ttfamily",
    "upshape",
    "itshape",
    "slshape",
    "scshape",
    "bfseries",
    "mdseries",
    "lfseries"
]
_UNWRAPPABLE_TEX_CMDS = [
    "au",  # short form of an author command, is always wrapped in \author{}
    "auth",  # same as au
    "city",  # specify the city of an affiliation
    "country",  # specify the country of an affiliation
    "cwanon",  # author anonymization (coop-writing)
    "department",  # specify the department of an affiliation
    "fnm",  # command to define the given name of an author (forename)
    "fnms",  # command to define the given name of an author (forename)
    "href",  # mostly used for emails, but sometimes as affiliation links with the affiliation name: \href{url}{name}
    "lowercase",  # text to lower case
    "makebox",  # command to prevent line breaks inside its content, has optional args in [...]
    "maketextuppercase",  # turns text into upper case
    "mbox",  # command to prevent line breaks inside its content
    "orgaddress",  # organisation address
    "orgdiv",  # organisation department
    "orgname",  # institution name
    "snm",  # command to define the family name of an author (surname)
    "sfx",  # surname suffix (Jr/Sr etc)
    "spfx",  # surname prefix (van der ...)
    "sur",  # command to define the family name of an author (surname)
    "text",  # no idea why people use it in text...
    "textbf",  # bold font
    "textit",  # italic font
    "textlf",  # light weight
    "textmd",  # medium weight
    "textnormal",  # default font
    "textrm",  # roman font
    "textsc",  # small caps
    "textsf",  # sans serif font
    "textsl",  # slanted shape
    "texttt",  # monospace font
    "textup",  # upright shape
    "underline",  # underline text
    "uppercase",  # text to upper case
]
# styles can also be their own commands -> \cmd{text} instead of {\cmd text}
# use a set to ignore duplicates, but switch back to a list
_UNWRAPPABLE_TEX_CMDS = set(_UNWRAPPABLE_TEX_CMDS + _LATEX_STYLES)


def split_on_separator(text: str) -> list[str]:
    # not sure if python would run strip 2x if `[part.strip() for .... if len(part.strip()) > 0]`
    return [spart for part in regex.split(LATEX_SEPARATORS, text) if len(spart := part.strip()) > 0]


def _trie_regex(parts: list[str] | set[str]) -> str:
    trie = Trie()
    for part in parts:
        trie.add(part)

    return trie.pattern()


# useful if a command has multiple nested constructs and regex complains about
# ambiguous group names.
def _get_nested_with_group_name(group_name: str) -> str:
    return (
        fr"(?P<{group_name}>"
        r"\{"
        fr"([^{{}}]|(?&{group_name}))*"
        r"\}"
        r")"
    )


# @formatter:off
# only works with regex lib, not re
NESTED_CONTENT_IN_CURLY_STR = (
    r"(?P<ne>"                                   # start a named capturing group called "ne"
        r"\{"                                    # non-escaped, opening curly brace
            r"([^{}]|(?&ne))*"                   # match any non-curly brace or start a recursive pattern containing the group "ne" 
        r"\}"                                    # non-escaped, closing curly brace
    r")"                                         # close named capturing group
)
NESTED_CONTENT_IN_CURLY = regex.compile(NESTED_CONTENT_IN_CURLY_STR)

# for commands like \href{}{} which do not work with:
# \href{NESTED_CONTENT_IN_CURLY}{NESTED_CONTENT_IN_CURLY}
# as the group name "ne" is ambiguous in that case. Thus, the second group needs another name (or index)
# since the second {} might be optional this needs to be reflected as well
DOUBLE_NESTED_CONTENT_IN_CURLY_STR = (
    f"{NESTED_CONTENT_IN_CURLY_STR}"
    r"\s*"
    r"(?:"
        r"(?P<net>"
            r"\{"
                r"([^{}]|(?&net))*"
            r"\}"
        r")"
    r")?"
)
DOUBLE_NESTED_CONTENT_IN_CURLY = regex.compile(DOUBLE_NESTED_CONTENT_IN_CURLY_STR)

NESTED_CONTENT_IN_BRACKETS_STR = (
    r"(?P<ne>"
        r"\["
            r"([^\[\]]|(?&ne))*"
        r"\]"
    r")"
)
NESTED_CONTENT_IN_BRACKETS = regex.compile(NESTED_CONTENT_IN_CURLY_STR)

AUTHORSHIP = regex.compile(
    r"(?<!\\(?:(?:re)?newcommand|def)\s*)"       # do not match a command definition (negative lookbehind)
    r"\\"                                        # backslash
    f"{_trie_regex(_AUTHOR_CMDS + _AFFILIATION_CMDS)}"  # regex generated by trie structure for known author and affiliation commands
    r"\*?"                                       # have an optional asterisk
    r"\s*"                                       #
    f"{NESTED_CONTENT_IN_BRACKETS_STR}*"
    r"\s*"                                       #
    f"{_get_nested_with_group_name("net")}"     # e.g. authorinfo{names}{affiliation}{email} or addauthor{}{}
    f"{_get_nested_with_group_name("ned")}?"     # e.g. authorinfo{names}{affiliation}{email} or addauthor{}{}
    f"{_get_nested_with_group_name("nev")}?",     # e.g. authorinfo{names}{affiliation}{email} or addauthor{}{}
    regex.IGNORECASE
)

AUTHORSHIP_ENV = regex.compile(
    r"(?<!\\(?:(?:re)?newcommand|def)\s*)"       # do not match a command definition (negative lookbehind)
    r"\\"
    r"(?:mdxauthorstart\{\}|begin\{author\})"  
    r"\s*"
    r".*?"
    r"(?:mdxauthorend\{\}|end\{author\})",
    regex.IGNORECASE
)

# latex suggested syntax of \a{b} with a being the combining char and b being the char. however, curly braces are
# optional and thus \`e will be valid as well. since stuff like \ca could be a command we will ignore characters of
# the alphabet as the combining char. Furthermore, the char is limited to one char in the case without curly braces.
# sources:
# - https://en.wikibooks.org/wiki/LaTeX/Special_Characters
# - Table  5: https://tug.ctan.org/info/symbols/comprehensive/symbols-a4.pdf
# - Table 19: https://tug.ctan.org/info/symbols/comprehensive/symbols-a4.pdf
LATEX_SPECIAL_CHARS_DIACRITIC = regex.compile(
    r"(?:"
        r"(?<!\\)\\"                             # e.g.: "\H{a}"
        r"(?P<c_char>[\"'.=^`|~bcCdfhHkrtuUv])" # group for the combining char, group(c_char)
        r"\{"
                r"(?P<char>[\\a-zA-Z]{0,2})"      # group for the char, can be empty, 1 char, or 2 chars, group(char)
        r"\}"
        r"|"                                     # OR e.g.: "\'e"
        r"(?<!\\)\\"
        r"(?P<c_char>[\"'.=^`|~])"                # limited set of combining chars
        r"(?P<char>[\a-zA-Z])"                   # exactly one char instead of zero to two
        r"|"                                     # OR e.g.: "{\aa}"
        r"\{"
            r"\\"
            r"(?P<char>[\\a-zA-Z]{1,2})"
        r"\}"
        "|"                                      # OR e.g.: "{\'e}"
        r"\{"
            r"\\"
            r"(?P<c_char>[\"'.=^`|~])"
            r"(?P<char>[\\a-zA-Z])"
        r"\}"
        "|"                                      # or e.g.: "{\v s}"
        r"\{?"
            r"(?<!\\)\\"
            r"(?P<c_char>[\"'.=^`|~bcCdfhHkrtuUv])"
            r" "
            r"(?P<char>[a-zA-Z])"
        r"\}?"
        "|"                                      # or e.g.: "\o "
        r"(?<!\\)\\"
        r"(?i)"                                  # enable "ignore case" flag
        r"(?P<char>[ijlo])"
        r"(?-i)"                                 # disable "ignore case" flag
        r"(?: |\{\})"
        "|"                                      # or e.g. "\AA "
        r"(?<!\\)\\"
        r"(?i)"                                  # enable "ignore case" flag
        r"(?P<char>(?:aa|ae|dj|dh|ij|ng|oe|ss|th))"
        r"(?-i)"                                 # disable "ignore case" flag
        r"(?: |\{\})"
    r")"
)

LATEX_USELESS_CMDS_NO_ARGS = regex.compile(
    r"\\"
    f"{_trie_regex(_USELESS_TEX_CMDS_NO_ARGS)}",
    regex.IGNORECASE
)

LATEX_USELESS_CMDS = regex.compile(
    r"\\"
    f"{_trie_regex(_USELESS_TEX_CMDS)}"
    r"(?:\[[^]]*\]\s*)*"                           # optional [...]-args, can appear multiple times
    f"(?:{_get_nested_with_group_name('neo')})"
    r"\s*"
    f"(?:{_get_nested_with_group_name('net')})?"
    r"\s*"
    f"(?:{_get_nested_with_group_name('ned')})?",
    regex.IGNORECASE
)

LATEX_CMDS_TO_UNWRAP = regex.compile(
    r"\\"
    f"{_trie_regex(_UNWRAPPABLE_TEX_CMDS)}"
    r"(?:\[[^]]*\]\s*)*"                           # optional [...]-args, can appear multiple times
    f"(?P<cnt1>{_get_nested_with_group_name('neo')})"
    r"\s*"
    f"(?P<cnt2>{_get_nested_with_group_name('net')})?"
    r"\s*"
    f"(?P<cnt3>{_get_nested_with_group_name('ned')})?",
    regex.IGNORECASE
)


# only matches on the beginning of the string, ex:
# "\rm this is text in a roman font"
#  ^^^^
# but not "\author{\rm ... }"
LATEX_STYLES_START = regex.compile(
    r"^"  # check for beginning of string
    r"(?:"
        r"\\"
        f"{_trie_regex(_LATEX_STYLES)}"
        r"\s*"
    r")+"  # + since for example "\tt\small " is valid
    r"\s",
    regex.IGNORECASE
)

LATEX_STYLES = regex.compile(
     r"(?<!\\)\{"  # non-escaped curly brace
    r"\s*"
    r"(?:"
        r"\\"
        f"{_trie_regex(_LATEX_STYLES)}"
        r"\s*"
    r")+"  # + since for example "{\tt\small " is valid
    r"\s",
    regex.IGNORECASE
)

LATEX_STYLES_NO_CURLY = regex.compile(
    r"(?<!\\|\{)\\"
    f"{_trie_regex(_LATEX_STYLES)}"
    r"\s",
    regex.IGNORECASE
)

LATEX_SEPARATORS_CMDS_ONLY_STR = (
    r"\\(?:and|qq?uad|cdot)\s*"
)
LATEX_SEPARATORS_CMDS_ONLY = regex.compile(LATEX_SEPARATORS_CMDS_ONLY_STR, regex.IGNORECASE)

LATEX_SEPARATORS_STR = (
    r"(?:"
        f"{LATEX_SEPARATORS_CMDS_ONLY_STR}"
        r"|"
        r","
        r"|"
        r"\sand\s"
    r")"
)
LATEX_SEPARATORS = regex.compile(LATEX_SEPARATORS_STR, regex.IGNORECASE)

# handles:
# \  -> escaped space (for multiple spaces)
# \, -> thin space
# \! -> negative of thin space
# \> -> medium space
# \: -> medium space
# \; -> thick space
LATEX_SPACING = regex.compile(
    r"(?<!\\)"     # make sure there is no \ before the spacing -> as "\\," is not spacing but a newline with a comma
    r"\\[ ,!>:;]"
)

# src:
# - https://www.overleaf.com/learn/latex/Lengths_in_LaTeX
# - https://en.wikibooks.org/wiki/LaTeX/Lengths
LATEX_MEASUREMENTS = regex.compile(
    r"\["
        r"-?(?:[0-9]+)?\.?[0-9]+(?:pt|mm|cm|in|ex|em|mu|sp|bp|pc|dd|cc|nd|nc)"
    r"\]",
    regex.IGNORECASE
)

# src: https://en.wikibooks.org/wiki/LaTeX/Special_Characters#Other_symbols
LATEX_ESCAPED_CHARS = regex.compile(
    r"(?<!\\)\\"
    r"(?P<char>[%${}_#&])"
)

# ignores commands with some cat src chars that are not normally used for command definitions, like "_" or "@".
# while possible, they should not be used and mostly require some workaround, which means they are mostly defined by
# the author or imported from some obscure package.
# "command"  references latex macros or, to be more precise, control words.
LATEX_FULL_COMMAND = regex.compile(
    r"(?<!\\)"                    # ignore \\
    r"\\"
    r"(?P<name>[a-z][a-z0-9]+)"   # digits can be in command names, but not as the first character
    r"\*?"                        # optional asterisk
    r"\s*"
    r"(?P<opt_args>\[[^]]*\]\s*)*"
    f"(?P<cnt1>{_get_nested_with_group_name('neo')})"
    r"\s*"
    f"(?P<cnt2>{_get_nested_with_group_name('net')})?"
    r"\s*"
    f"(?P<cnt3>{_get_nested_with_group_name('ned')})?",
    regex.IGNORECASE
)

LATEX_USELESS_EMAIL = regex.compile(
    # email cmd without arguments, we can not place it in USELESS_CMDS_NO_ARGS as the same command can be used with
    # an argument that we want to remove aswell. As we first remove USELESS_CMDS_NO_ARGS and only afterward
    # USELESS_CMDS, we would remove the command and leave its argument (the email). Thus, we remove USELESS_CMDS_NO_ARGS
    # first, then USELESS_CMDS and only then leftover \email without arguments.
    r"\\emails?\s"
)

LATEX_EMAIL = regex.compile(
    r"\(?"
    r"(?:\\[a-z]*email|e-?mails?:|contacts?:)?"
    r"\s*"
    r"(?:"
        # single email
        r"\\?\{?"
            # the following line is from https://emailregex.com/ and good enough
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        r"\\?\}?"
        "|"
        # multiple names as a set before the domain part
        r"\\?\{?"
            r"\\?\{"
                r"[a-zA-Z0-9_.+, -]+"
            r"\\?\}"
            r"@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        r"\\?\}?"
    r")"
    r"\)?",
    regex.IGNORECASE
)

LATEX_DESCRIPTORS = regex.compile(
    r"\s(e-?mails?|website|link):\s",
    regex.IGNORECASE
)

LATEX_DOCUMENTCLASS = regex.compile(
    r"\\documentclass"
    r"\s*"
    r"(?:\[[^]]+]\s*)*"
    r"\s*"
    f"(?P<name>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

LATEX_COMMENT_BLOCK = regex.compile(
    r"\\begin\s*\{\s*comment\s*\}"
        r".*?"
    r"\\end\s*\{\s*comment\s*\}",
    regex.IGNORECASE
)

_HYPHEN_VARIANTS_STR = r"[−\-]"  # \u2212 (minus sign) vs \u002d (hypen-minus)

_ORCID_ID_STR = (
    # 0000-1111-2222-3333
    "[0-9]{4}"
    "(?:"
        f"{_HYPHEN_VARIANTS_STR}"
        "[0-9]{4}"
    "){2}"
    f"{_HYPHEN_VARIANTS_STR}"
    "[0-9]{3}[0-9X]"  # last char can be an X
)

LATEX_PLAIN_ORCID_ID = regex.compile(
    r"orcid"
    r"(?:\s*id)?"
    r":?"
    r"\s*"
    f"{_ORCID_ID_STR}",
    regex.IGNORECASE
)

LATEX_URL_ORCID_ID_STR = (
    r"(?:https?://)?orcid\.org/"
    f"{_ORCID_ID_STR}"
)
LATEX_URL_ORCID_ID = regex.compile(LATEX_URL_ORCID_ID_STR, regex.IGNORECASE)

# used for link to orcid with an orcid icon in the second argument of href
LATEX_HREF_ORCID_ID = regex.compile(
    r"\\href\{"
        f"{LATEX_URL_ORCID_ID_STR}"
    r"\}"
    r"\s*"
    f"{NESTED_CONTENT_IN_CURLY_STR}",
    regex.IGNORECASE
)

LATEX_ORCID_CMDS = regex.compile(
    r"\\"
    r"(?:lmcs|my)?"
    r"orcid"
    r"(?:"
        r"[a-z]{1,2}"  # chars as enumeration or author name abbreviations (custom)
        r"|"
        r"[ivx]+"  # roman numerals (max: 30 (XXX))
        r"|"
        r"i(?:con|d)"  # icon or id
        r"|"
        r"link"
        r"|"
        r"a(?:uthor[a-z]{0,2}|ffil)"  # chars as enumeration or author name abbreviations (custom)
    r")?"
    r"(?:\[[^]]*\]\s*)*"                           # optional [...]-args
    f"(?:{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# \s{2,} would be more accurate for the name, but this also matches linebreaks to convert to spaces
# a 2 in 1 solution so to speak
SPACE_MULTI = regex.compile(
    r"\s+"
)

# regular expressions to retrieve content of specific structures
ADDRESS_CONTENT = regex.compile(
    r"\\address"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AFFADDR_CONTENT = regex.compile(
    r"\\affaddr"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AFFIL_CONTENT = regex.compile(
    r"\\affil"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AFFILIATION_CONTENT = regex.compile(
    r"\\affiliation"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AFFMARK_CONTENT = regex.compile(
    r"\\affmark"
    f"(?P<cnt>{NESTED_CONTENT_IN_BRACKETS_STR})",
    regex.IGNORECASE
)

ALIGNAUTHOR_CONTENT = regex.compile(
    r"\\alignauthor"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AUTHOR_CONTENT = regex.compile(
    r"\\author"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AUTHORNAME_CONTENT = regex.compile(
    r"\\authorname"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

COMP_SOC_ITEMIZE_CONTENT = regex.compile(
    r"\\ieeecompsocitemizethanks"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

FOOTNOTE_CONTENT = regex.compile(
    r"\\footnote"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

# reverse = scanning from end to start
FOOTNOTE_CONTENT_REVERSE = regex.compile(
    r"\\footnote"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE | regex.REVERSE
)

FOOTNOTEMARK_CONTENT_STR = (
    r"\\footnotemark"
    f"(?P<cnt>{NESTED_CONTENT_IN_BRACKETS_STR})"
)
FOOTNOTEMARK_CONTENT = regex.compile(FOOTNOTEMARK_CONTENT_STR, regex.IGNORECASE)

INST_CONTENT = regex.compile(
    r"\\inst"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

INSTITUTE_CONTENT = regex.compile(
    r"\\institute"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

INSTITUTION_CONTENT = regex.compile(
    r"\\institution"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

MATH_MODE_CONTENT_STR = (
    r"\$"
        r"(?P<cnt>[^$]+)"
    r"\$"
)
MATH_MODE_CONTENT = regex.compile(MATH_MODE_CONTENT_STR)

MATH_TEXT_CMD_CONTENT = regex.compile(
    r"\\text"
    r"("
        f"{NESTED_CONTENT_IN_CURLY_STR}"
    r")",
    regex.IGNORECASE
)

NAME_CONTENT = regex.compile(
    r"\\name"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

PARBOX_CONTENT = regex.compile(
    r"\\parbox"
    f"{_get_nested_with_group_name('neo')}"  # this is the width, useless for anything
    r"\s*"
    f"(?P<cnt>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

SUP_CONTENT = regex.compile(
    r"\\sup"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

TEXTSUPERSCRIPT_CONTENT = regex.compile(
    r"\\t(?:s|extsuperscript)"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

THANKS_CONTENT = regex.compile(
    r"\\thanks"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

THANKSREF_CONTENT = regex.compile(
    r"\\thanksref"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

TITLENOTE_CONTENT = regex.compile(
    r"\\titlenote"
    f"(?P<cnt>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# regexes for commands appearing multiple times behind each other
# used to join those commands to a single one
# each regex should match two commands behind each other and should use the following groups for their content:
# - first argument: "first"
# - second argument: "second"
# the groups are allowed to contain the curly braces if the command might include nested structures
AFFILIATION_MULTI = regex.compile(
    r"\\affiliation"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*(?:\\\\|\\and)?\s*"
    r"\\affiliation"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

AFFIL_MULTI = regex.compile(
    r"\\affil"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\affil"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

MATH_MODE_MULTI = regex.compile(
    r"\$(?P<first>[^$]+)\$"
    r"\s*"
    r"\$(?P<second>[^$]+)\$"
)

AUTHOR_REF_MARK_MULTI = regex.compile(
    r"\\(?:ieee)?authorrefmark"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\(?:ieee)?authorrefmark"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

TEXTSUPERSCRIPT_MULTI = regex.compile(
    r"\\textsuperscript"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\textsuperscript"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

THANKSREF_MULTI = regex.compile(
r"\\thanksref"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\thanksref"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

SUP_MULTI = regex.compile(
    r"\\sup"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\sup"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

AFFMARK_MULTI = regex.compile(
    r"\\affmark"
    r"\["
        r"(?P<first>[^]]+)"
    r"\]"
    r"\s*"
    r"\\affmark"
    r"\["
        r"(?P<second>[^]]+)"
    r"\]",
    regex.IGNORECASE
)

FOOTNOTEMARK_MULTI = regex.compile(
    r"\\footnotemark"
    r"\["
        r"(?P<first>[^]]+)"
    r"\]"
    r"\s*"
    r"\\footnotemark"
    r"\["
        r"(?P<second>[^]]+)"
    r"\]",
    regex.IGNORECASE
)

INSTITUTE_MULTI = regex.compile(
    r"\\institute"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\institute"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

AUTHORBLOCKA_MULTI = regex.compile(
r"\\(?:ieee)?authorblocka"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\(?:ieee)?authorblocka"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

AUTHORBLOCKN_MULTI = regex.compile(
r"\\(?:ieee)?authorblockn"
    f"(?P<first>{_get_nested_with_group_name('neo')})"
    r"\s*"
    r"\\(?:ieee)?authorblockn"
    f"(?P<second>{_get_nested_with_group_name('net')})",
    regex.IGNORECASE
)

# scheme:
# \author[short]{... \rsuper a}
# \address{{\lsuper a}...}
#
# example (from https:arxiv.org/src/0706.0523):
# [
#     "\\author[R. Jhala]{Ranjit Jhala\\rsuper a}",
#     "\\address{{\\lsuper a}University of California, San Diego 9500 Gilman Drive La Jolla, CA 92093}",
#     "\\author[K. L. McMillan]{Kenneth L. McMillan\\rsuper b}",
#     "\\address{{\\lsuper b}Cadence Berkeley Laboratories 1995 University Ave., Suite 460 Berkeley, CA 94704 }"
# ]
LR_SUPER_AUTHOR = regex.compile(
    r"\\author"                                  # the author command
    r"\[[^]]+\]"                                 # anything that isn't a closing bracket inside brackets (short name)
    r"\{"                                        # opening curly brace
        r"(?P<name>.+?)\s*\\rsuper\s*"           # anything that stands before \rsuper (non-greedy, no whitespaces), group(name)
        r"(?P<id>.*?)"                           # non-greedy match for the identifier of the address, group(id) 
    r"\}",                                       # closing curly brace
    regex.IGNORECASE
)

LR_SUPER_AFFILIATION = regex.compile(
    r"\\address"                                 # the address command
    r"\{\{"                                      # two opening curly braces, one for the address, one for the affiliation identifier
            r"\\lsuper\s*\{?(?P<id>.*?)\}?\s*"   # the \lsuper command followed by the identifier, group(id)
        r"\}"                                    # the closing curly brace for \lsuper 
        r"(?P<name>.*)"                          # the name of the affiliation, group(name)
    r"\}",                                       # closing curly brace of the address command
    regex.IGNORECASE
)

# scheme:
# \author[1]{...}
# \address[1]{...}
#
# example (from: https://arxiv.org/src/0708.2255):
# [
#     "\\author[1]{Jeremy G. Siek}",
#     "\\author[2]{Andrew Lumsdaine}",
#     "\\address[1]{Deptartment of Electrical and Computer Engineering, University of Colorado at Boulder, USA}",
#     "\\address[2]{Computer Science Department, Indiana University, USA}"
# ]
OPT_ARG_ID_AUTHOR = regex.compile(
    r"\\author"                                  # the author command
    r"\[(?P<id>[^]]+)\]"                         # address identifier, group(id)
    r"\{"                                        # opening curly brace
        r"(?P<name>.+?)"                         # non-greedy name, group(name)
    r"\}",                                       # closing curly brace
    regex.IGNORECASE
)

OPT_ARG_ID_AFFILIATION = regex.compile(
    r"\\address"                                 # the address command
    r"\[(?P<id>[^]]+)\]"                         # address identifier, group(id)
    r"\{"                                        # two opening curly brace
        r"(?P<name>.*?)"                         # non-greedy name of the affiliation, group(name)
    r"\}",                                       # closing curly brace
    regex.IGNORECASE
)


# \thanks used for affiliations
# ex: (https://arxiv.org/src/0809.4812)
# \author{
#     Eric Feron \thanks{Dutton/Ducoffe Professor of Aerospace Software Engineering, Georgia Institute of Technology. feron@gatech.edu} \and
#     Fernando Alegre \thanks{College of Computing, Georgia Institute of Technology. fernando@gatech.edu}
# }
AUTHOR_THANKS_AFF = regex.compile(
    r"(?P<name>.*?)"                                # named capturing group for the author name, group(name)
    r"\\thanks"
    f"(?P<aff>{NESTED_CONTENT_IN_CURLY_STR})",       # named capturing group for the content of thanks
    regex.IGNORECASE
)


# authorinfo, {} for author and next {} for affiliation, 3rd {} would be for email (not included)
# same regex can be applied to oneauthor or twoauthors
# ex: (https://arxiv.org/src/0707.4166)
# \authorinfo{Todd L. Veldhuizen} {Electrical and Computer Engineering University of Wateroo, Canada}
EXT_AUTHORINFO = regex.compile(
    f"(?P<name>{_get_nested_with_group_name('first')})"
    r"\s*"
    f"(?P<aff>{_get_nested_with_group_name('second')})"
)


# authors separated by \and, references to affiliation via \footnotemark
# ex: (https://arxiv.org/src/0806.0314)
# \author{Nicholas C. Manoukis\footnotemark[2] \and Eric C. Anderson\footnotemark[4] \and \footnotemark[2] Section of Vector Biology, Laboratory of Malaria and Vector Research National Institute of Allergy and Infectious Diseases, National Institutes of Health 12735 Twinbrook Parkway, Bethesda, MD 20892 USA \vspace{2mm} \footnotemark[4] Fisheries Ecology Division, Southwest Fisheries Science Center National Oceanic and Atmospheric Administration 110 Shaffer Road, Santa Cruz, CA 95060 USA },
FOOTNOTEMARK_AUTHOR = regex.compile(
    r"(?P<name>.*)"
    r"\s*\\footnotemark"
    r"\["
        r"(?P<ref_id>[^]]+)"
    r"\]",
    regex.IGNORECASE
)

FOOTNOTEMARK_AFFILIATION = regex.compile(
    r"\\footnotemark"
    r"\["
        r"(?P<ref_id>[^]]+)"
    r"\]\s*"
    r"(?P<name>.*)",
    regex.IGNORECASE
)


# rrauthor has \and or comma separated authors. \thanks{} (optional) is used for the affiliation.
EXT_RRAUTHOR_THANKS_WITH_REF = regex.compile(
    r"\\thanks"
    r"(?:"                                        # optional capturing group for pre-existing ref_id
        r"\["
            r"(?P<ref_id>[^]]+)"                 # the ref id, group(ref_id)
        r"\]"
    r")?"
    r"(?P<cnt>"                                   # capturing group for the command content (affiliation data), group(cnt)
        f"{NESTED_CONTENT_IN_CURLY_STR}"
    r")",
    regex.IGNORECASE
)


# articleauthors has \author{} and \aff{} commands for each author in that order
# ex: (https.//arxiv.org/src/1308.3847)
# \ARTICLEAUTHORS{
#     \AUTHOR{Roberto Bagnara} \AFF{BUGSENG srl and Dept.\ of Mathematics and Computer Science, University of Parma, Italy, \EMAIL{\url{bagnara@cs.unipr.it}}, \URL{\url{http://www.cs.unipr.it/ bagnara}}}
#     \AUTHOR{Matthieu Carlier} \AFF{INRIA Rennes Bretagne Atlantique, France}
#     \AUTHOR{Roberta Gori} \AFF{Dept.\ of Computer Science, University of Pisa, Italy, \EMAIL{\url{gori@di.unipi.it}}, \URL{\url{http://www.di.unipi.it/ gori}}}
#     \AUTHOR{Arnaud Gotlieb} \AFF{Certus Software V\&V Center, SIMULA Research Laboratory, Norway, \EMAIL{\url{arnaud@simula.no}}, \URL{\url{http://simula.no/people/arnaud}}}
# }
EXT_ARTICLEAUTHORS_AUTHOR_AFF = regex.compile(
    r"\\author"
    fr"(?P<name>{_get_nested_with_group_name('first')})"
    r"\s*"
    r"\\aff"
    fr"(?P<aff>{_get_nested_with_group_name('second')})",
    regex.IGNORECASE
)


# authorblockN for names and authorblockA for affiliations. includes ieeeauthorblocks. there are two different styles:
# - authorblockN for each author and the subsequent authorblockA is their affiliation
# - authorblockN with multiple authors and the subsequent authorblockA is their affiliation
# ex: (https://arxiv.org/src/0810.3468)
# \author{ \authorblockN{ Muthiah Annamalai } \authorblockA{ University of Texas, Arlington, USA, email: muthiah.annamalai@uta.edu } \and \authorblockN{ Leela Velusamy } \authorblockA{Department of Computer Science \& Engineering, National Institute of Technology, Tiruchirapalli, India. email: leela@nitt.edu } }
EXT_AUTHORBLOCK_BLOCKS = regex.compile(
    r"\\(?:ieee)?authorblock(?P<block_type>[an])"
    f"(?P<block_content>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# authorblockN for names and authorblockA for affiliations, each block has a refmark. there are two different styles:
# # - authorblockN for each author and the referenced authorblockA is their affiliation
# # - authorblockN with multiple authors and the referenced authorblockA is their affiliation
# example (https://arxiv.org/src/0810.3468):
# \author{\IEEEauthorblockN{Adam Barker\IEEEauthorrefmark{1}, Jano I. van Hemert\IEEEauthorrefmark{2}, Richard A. Baldock\IEEEauthorrefmark{3} and Malcolm P. Atkinson\IEEEauthorrefmark{2}}. \IEEEauthorblockA{\IEEEauthorrefmark{1}Department of Engineering Science, University of Oxford, UK.} \IEEEauthorblockA{\IEEEauthorrefmark{2}National e-Science Centre, School of Informatics, University of Edinburgh, UK.} \IEEEauthorblockA{\IEEEauthorrefmark{3}Human Genetics Unit, Medical Research Council. UK}}
EXT_AUTHORBLOCK_REF_AUTHOR = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\(?:ieee)?authorrefmark"
        f"(?P<ref_id>{NESTED_CONTENT_IN_CURLY_STR})"    # named capturing group for command content, group(content)
    r"\s*(?:,|(?:\\)?and)?\s*",
    regex.IGNORECASE
)

EXT_AUTHORBLOCK_REF_AFFILIATION = regex.compile(
    r"\\(?:ieee)?authorrefmark"
    f"(?P<ref_id>{NESTED_CONTENT_IN_CURLY_STR})"    # named capturing group for command content, group(content)
    r"\s*"
    r"(?P<name>.*)"
    r"\s*",
    regex.IGNORECASE
)


# authorblock with references between author and affiliation using latex math mode
# ex: (https://arxiv.org/src/0911.0136)
# \author{
#     \IEEEauthorblockN{Yu Huang$^{1,2}$, Jianping Yu$^{1,2}$, Jiannong Cao$^3$, Xiaoxing Ma$^{1,2}$, Xianping Tao$^{1,2}$, Jian Lu$^{1,2}$}
# 	  \IEEEauthorblockA{$^1$State Key Laboratory for Novel Software Technology Nanjing University, Nanjing 210093, China $^2$Department of Computer Science and Technology Nanjing University, Nanjing 210093, China \{yuhuang, xxm, txp, lj\}@nju.edu.cn, yujianping@ics.nju.edu.cn} $^3$Internet and Mobile Computing Lab, Department of Computing Hong Kong Polytechnic University, Hong Kong, China csjcao@comp.polyu.edu.hk
# }
MATH_AUTHOR_REF = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    f"(?P<ref_id>{MATH_MODE_CONTENT_STR})"
)

MATH_AFFILIATION = regex.compile(
    f"(?P<ref_id>{MATH_MODE_CONTENT_STR})"
    r"\s*"
    r"(?P<name>[^$]+)"
)

# author separated by \and, with their affiliation in \institute{}
# ex: (https://arxiv.org/src/0911.2034)
# \author{
#     Edgar G. Daylight \institute{a.k.a. K. Van Oudheusden,\ Institute of Logic, Language, and Computation,\ University of Amsterdam, The Netherlands} \and
#     Sandeep K. Shukla \institute{Department of Electrical\ \& Computer Engineering,\ Virginia Tech., USA} \and
#     Davide Sergio \institute{Institute of Logic, Language, and Computation,\ University of Amsterdam, The Netherlands}
# }
VAL_AUTHOR_INSTITUTE_SEP_TEX_AND = regex.compile(
    r"\s*"
    r"(?:"
        r".*?"
        r"\\institute"
        f"{NESTED_CONTENT_IN_CURLY_STR}"
        r"\s*(?:\\and\s*)?"
    r")+"
    r"\s*",
    regex.IGNORECASE
)

EXT_AUTHOR_INSTITUTE_SEP_TEX_AND = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\institute"
    f"(?P<aff>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# author has a footnote for their affiliation
# ex: (https://arxiv.org/src/1703.03657)
# \author{
#     Asim Abdulkhaleq\footnote{Institute of Software Technology, University of Stuttgart, Asim.Abdulkhaleq@informatik.uni-stuttgart.de},
#     Stefan Wagner\footnote{Institute of Software Technology, University of Stuttgart, Stefan.Wagner@informatik.uni-stuttgart.de},
#     Daniel Lammering \footnote{Continental, Regensburg, Germany, Daniel.Lammering@continental-corporation.com},
#     Hagen Boehmert\footnote{Continental, Frankfurt am Main, Germany, Hagen.Boehmert@continental-corporation.com } and
#     Pierre Blueher \footnote{Continental, Frankfurt am Main, Germany, Pierre.Blueher@continental-corporation.com}
# }
EXT_AUTHOR_FOOTNOTE = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\footnote"
    f"(?P<aff>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# author has a \textsuperscript{} to reference the affiliation. the affiliation also has a t\extsuperscript{}
# some use $...$ inside the curly braces, but most do not.
# ex: (https://arxiv.org/src/1301.1085)
# \author{
#     Charith Perera\textsuperscript{*+} \and
#     Arkady Zaslavsky\textsuperscript{+} \and
#     Peter Christen\textsuperscript{*} \and
#     Ali Salehi\textsuperscript{+} \and
#     Dimitrios Georgakopoulos\textsuperscript{+}\\
#     \textsuperscript{*}Research School of Computer Science, The Australian National University, \\Canberra, ACT 0200, Australia \
#     \textsuperscript{+}CSIRO ICT Center, Canberra, ACT, 2601, Australia
# }
AUTHOR_TEXTSUPERSCRIPT = regex.compile(
    r"(?P<name>.+)"
    r"\s*"
    r"\\textsuperscript"
    f"(?P<ref>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

AFFILIATION_TEXTSUPERSCRIPT = regex.compile(
    r"\\textsuperscript"
    f"(?P<ref>{NESTED_CONTENT_IN_CURLY_STR})"
    r"\s*"
    r"(?P<name>.+)",
    regex.IGNORECASE
)

# same as the other \textsuperscript{} case but the affiliation uses \textsuperscript{ref}{name}
# ex: (https://arxiv.org/src/1910.05835)
# \author{
#     Christopher A. Choquette-Choo,\textsuperscript{1,5}
#     David Sheldon,\textsuperscript{2}
#     Jonny Proppe,\textsuperscript{3,4}
#     John Alphonso-Gibbs,\textsuperscript{2}
#     Harsha Gupta\textsuperscript{2}\\
#     \textsuperscript{1}{Work completed while at Intel PSG, San Jose, California, United States}\\
#     \textsuperscript{2}{Intel PSG, San Jose, California, United States}\\
#     \textsuperscript{3}{University of Toronto, Departments of Chemistry and Computer Science, Toronto, Ontario, Canada}\\
#     \textsuperscript{4}{{Current address}: University of Göttingen, Institute of Physical Chemistry, Göttingen, Germany}
# }
DOUBLE_TEXTSUPERCRIPT_AFFILIATION = regex.compile(
    r"\\textsuperscript"
    f"{_get_nested_with_group_name('first')}"
    r"\s*"
    f"{_get_nested_with_group_name('second')}",
    regex.IGNORECASE
)

DOUBLE_TEXTSUPERSCRIPT_AFFILIATION_CONTENT = regex.compile(
    r"\\textsuperscript"
    f"(?P<ref>{_get_nested_with_group_name('first')})"
    r"\s*"
    f"(?P<name>{_get_nested_with_group_name('second')})",
    regex.IGNORECASE
)


# author names appear first. after that there is an \IEEEcompsocitemizethanks{}. In there are \IEEEcompsocthanksitem
# that are structured like "name(s) is/are with affiliation"
# ex: (https://arxiv.org/src/1611.05994)
# \author{
#     Davide Fucci, Hakan Erdogmus, Burak Turhan, Markku Oivo, Natalia Juristo,
#     \IEEEcompsocitemizethanks{
#         \IEEEcompsocthanksitem D. Fucci, B. Turhan, M. Oivo, and N. Juristo are with the Department of Information Processing Science, University of Oulu, Finland\protect\\ E-mail: {name.surname}@oulu.fi
#         \IEEEcompsocthanksitem N. Juristo is also with Escuela Tecnica Superior de Ingenieros Informaticos, Universidad Politecnica de Madrid, Spain\protect\\ E-mail: natalia@fi.upm.es
#         \IEEEcompsocthanksitem H. Erdogmus is with Carnegie Mellon University, Silicon Valley Campus, USA.\protect\\ E-mail: hakan.erdogmus@sv.cmu.edu
#     }
# }
_PREDICATE_FILLERS = [
    "a",
    "affiliated",  # xyz is affiliated with
    "also",  # xyz is also with
    "an",
    "appointments",  # holds shared appointments with
    "assistant",  # xyz is an assistant professor with
    "associated",  # xyz is associated with
    "candidate",  # is a Ph.D candidate
    "currently",  # is currently with
    "doctoral",  # is a doctoral candidate at
    "full",  # is full professor of
    "graduate",  # is a graduate student at
    "head",  # is head of
    "master",  # is a master student
    "ph.d",  # is a Ph.D candidate
    "professor",  # is full professor of
    "shared",  # holds shared appointments with
    "student"  # is a graduate student at
]

PREDICATIVE_EXPRESSIONS = regex.compile(
    r"\s+"
    r"(?:is|are|was|were|works|holds)"
    r"\s+"
    fr"(?:{_trie_regex(_PREDICATE_FILLERS)}\s+)*"
    r"(?:of|with|at|to|in)"
    r"(?:\s+the)?"  # handle "the" in front of affiliation name
    r"\s+",
    regex.IGNORECASE
)


# author names are listed first with a reference to their affiliation using \affmark[].
# the affiliation are each in their own \affaddr{} and include the reference in a \affmark[].
# ex: (https://arxiv.org/src/1708.06046)
# \author{
#     S. Maetschke\affmark[1], R. Tennakoon\affmark[2], C. Vecchiola\affmark[1] and R. Garnavi\affmark[1]\\ \\
#     \affaddr{\affmark[1]IBM Research Australia, 5/204 Lygon Street, Melbourne VIC 3053}\\
#     \affaddr{\affmark[2]School of Engineering, RMIT University, 376 Swanston Street, Melbourne VIC 3000}\\ \\ \\%
# }
AFFMARK_AUTHOR = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\affmark"
    r"\["
        r"(?P<ref>[^]]+)"
    r"\]",
    regex.IGNORECASE
)

# the author name followed by \affil{}
# ex: (https://arxiv.org/src/1612.03103)
# \author{
#     Asim Abdulkhaleq
#     \affil{Institute of Software Technology, University of Stuttgart, Germany}
#     Stefan Wagner
#     \affil{Institute of Software Technology, University of Stuttgart, Germany}
# }
NAME_AFFIL = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\affil"
    f"(?P<aff>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)


# name followed by \affiliation{}
# ex: (https://arxiv.org/src/1112.3972)
# \author{
#     Emil Vassev\\
#     \affiliation{Lero - the Irish Software Engineering Research Centre}\\
#     \affiliation{University of Limerick, Limerick, Ireland}\\ \and
#     Serguei A. Mokhov\
#     \affiliation{Faculty of Engineering and Computer Science, Concordia University}\\
#     \affiliation{1455 de Maisonneuve Blvd. W, Montreal, QC, Canada}\\
# }
NAME_AFFILIATION = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\affiliations?"
    f"(?P<aff>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

NAME_SUP = regex.compile(
    r"(?P<name>.*?)"
    r"\s*"
    r"\\sup?"
    f"(?P<ref>{NESTED_CONTENT_IN_CURLY_STR})",
    regex.IGNORECASE
)

# @formatter:on
