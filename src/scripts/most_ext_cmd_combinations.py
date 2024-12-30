"""
Extract the most used command combinations of extracted commands.
"""
import util


def main():
    cmd_combinations = {}
    for paper_dir in util.get_paper_dirs():
        ext_cmds = util.read_json(paper_dir, util.CMDS_FILE)
        if not ext_cmds:
            continue

        cmds = ext_cmds.cmds
        if len(cmds) == 0:
            continue

        cmd_names = set()
        for cmd in cmds:
            scmd = cmd.sanitized_cmd
            args_index = scmd.find("{")
            args_index = i if (i := scmd[:args_index].find("[")) != -1 else args_index
            cmd_name = scmd[1:args_index]
            cmd_names.add(cmd_name)

        sorted_cmds = sorted(cmd_names)
        scmd_str = ", ".join(sorted_cmds)
        if scmd_str in cmd_combinations:
            cmd_combinations[scmd_str] += 1
        else:
            cmd_combinations[scmd_str] = 1

    print({k: v for k, v in sorted(cmd_combinations.items(), key=lambda x: -x[1])})


if __name__ == '__main__':
    main()
