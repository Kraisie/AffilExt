"""
Rates latex author and affiliation commands with a basic level of difficulty. Since longer list of authors are not
more difficult than shorter lists with similar syntax the number of backslashes, brackets and curly braces are put into
relation with the length of the command. However, this is still not perfect as shorter names also do not result in
easier commands.
The latex versions of umlauts and diacritics (see: https://en.wikibooks.org/wiki/LaTeX/Special_Characters) are also
not hard to handle but count like a command. Harder are commands which are custom as they need to be resolved. Due to
that issue the custom commands will not be handled in here as more difficult than normal command, although they are.
The real difficulty are commands that have multiple levels where some might be important while the one containing it
might not be as important. Thus, we include the maximum depths of the command in the calculation.
"""

import util


def get_cmd_depth(cmd_text: str) -> int:
    level = max_level = 0
    for c in cmd_text:
        if c == '{':
            level += 1
            if level > max_level:
                max_level = level
        elif c == '}':
            level -= 1

    return max_level


def main():
    commands = []
    for paper_dir in util.get_paper_dirs():
        ext_cmds = util.read_json(paper_dir, util.CMDS_FILE)
        if not ext_cmds or len(ext_cmds.cmds) == 0:
            continue

        cmds_str = " ".join([cmd.sanitized_cmd for cmd in ext_cmds.cmds])
        cmds_str = cmds_str.replace(r"\\", " ")
        backslash = cmds_str.count("\\")
        brackets = cmds_str.count("[")
        curly_braces = cmds_str.count("{")
        depth = get_cmd_depth(cmds_str)
        difficulty = ((backslash + brackets + curly_braces) * depth) / len(cmds_str)
        commands.append((cmds_str, difficulty))

    for cmd in sorted(commands, key=lambda x: -x[1]):
        cmd_str = cmd[0]
        cmd_score = cmd[1]
        print(f"{cmd_score} - {cmd_str}")


if __name__ == '__main__':
    main()
