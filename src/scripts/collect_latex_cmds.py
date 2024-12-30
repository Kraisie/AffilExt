"""
Get all used latex commands, display a top-list and enable searching for specific command names.
Can be limited to only search for commands in extracted commands.
"""

from pathlib import Path

import regex

import util
from definition import reg_exp, latex


def _find_commands(cmds, text):
    for m in regex.finditer(reg_exp.LATEX_FULL_COMMAND, text, overlapped=True):
        cmd_name = m.group("name").lower()
        if cmd_name not in cmds:
            cmds[cmd_name] = {"sample": m.group(0), "occ": 1}
        else:
            cmds[cmd_name]["occ"] += 1


def _all_commands(paper_dir: Path):
    tex_files = util.get_all_tex_files(paper_dir)
    cmds = {}
    for tex_file in tex_files:
        tex = latex.remove_comments(util.read(tex_file))
        if tex:
            _find_commands(cmds, tex)

    return dict(sorted(cmds.items(), key=lambda x: -x[1]["occ"]))


def _ext_commands(paper_dirs: list[Path]):
    cmds = {}
    for paper_dir in paper_dirs:
        ext_cmds = util.read_json(paper_dir, util.CMDS_FILE)
        if not ext_cmds:
            continue

        for cmd in ext_cmds.cmds:
            _find_commands(cmds, cmd.sanitized_cmd)

    return dict(sorted(cmds.items(), key=lambda x: -x[1]["occ"]))


def main():
    top_size = 10
    mode = input("Collect all latex commands or just extracted commands? [a/e]: ")
    cmds = _all_commands(util.get_papers_dir()) if mode == "a" else _ext_commands(util.get_paper_dirs())
    print(f"\nTop{top_size}:")
    for i, cmd in enumerate(list(cmds)[:top_size], start=1):
        print(f"{i}. '{cmd}' occurred {cmds[cmd]['occ']} times.")

    while query := input("\nSearch for a command name, q to quit: "):
        if query == "q":
            break

        query = query.strip().lower()
        if query in cmds:
            cmd = cmds[query]
            print(f"'{query}' occurred {cmd['occ']} times. Example: '{cmd['sample']}'")
        else:
            print(f"Found no command with the name '{query}'!")


if __name__ == "__main__":
    main()
