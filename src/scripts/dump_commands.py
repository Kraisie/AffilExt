"""
Dumps extracted commands to stdout based on user input. "Single commands" referencing to papers that only have one
extracted command. "Multi commands" referencing those that have at least two extracted commands. For most use-cases
piping the output into a file would be beneficial.
"""

import util


def main():
    mode = input("Dump single, multi or all commands? [single/multi/all] : ")
    match mode.strip()[0].lower():
        case "s":
            mode_filter = lambda x: len(x) == 1
        case "m":
            mode_filter = lambda x: len(x) > 1
        case "a" | _:
            mode_filter = lambda x: True

    doc_class = input("Do you want to filter for a document class name? (leave blank if not) : ")
    doc_class_filter = (lambda x: doc_class in x) if doc_class else (lambda x: True)

    cmd_name = input("Do you want to filter for a command name? (leave blank if not) : ")
    cmd_name_filter = (lambda x: x[1:].lower().startswith(cmd_name)) if cmd_name else (lambda x: True)

    for paper_dir in util.get_paper_dirs():
        ext_cmds = util.read_json(paper_dir, util.CMDS_FILE)
        if not ext_cmds:
            continue

        cmds = ext_cmds.cmds
        if mode_filter(cmds) and doc_class_filter(ext_cmds.documentclasses):
            sanitized_commands = [scmd for cmd in cmds if cmd_name_filter(scmd := cmd.sanitized_cmd)]
            if len(sanitized_commands) == 0:
                continue

            cmd_str = "\n".join(sanitized_commands)
            print(f"--- {paper_dir.name} ---\n{cmd_str}\n")


if __name__ == '__main__':
    main()
