import logging
from pathlib import Path

import regex

import threaded_run
import util
from definition import latex
from definition import reg_exp
from definition.data.ExtCmdData import ExtCmdData, LatexCmd

_logger: logging.Logger = logging.getLogger(__name__)


def _is_empty_command(cmd: str) -> bool:
    if "{" not in cmd:
        return True

    # if we get here the command has to have an opening and closing curly brace (due to the regex extraction)
    # thus, we do not need to worry about find() returning -1
    cmd_argument = cmd[cmd.find("{"):cmd.rfind("}")]
    return cmd_argument.strip("{} ") == ""


def _is_enclosed_cmd(cmds: list[dict], start: int, end: int) -> bool:
    # ignore matches inside bigger match e.g.: \affilitiation{\institute{...}, \city{...}, \country{...}}
    if not cmds or len(cmds) == 0:
        return False

    for command in reversed(cmds):  # start with last added cmd as that is the most probable to enclose current cmd
        if start > command["end_pos"]:
            # stop when far enough away from current cmd
            break

        if start > command["start_pos"] and end < command["end_pos"]:
            return True

    return False


def _extract_authorship_from_tex(pattern: regex.Pattern[str], tex: str, envs=None) -> list[dict]:
    cmds = []
    for authorship_match in regex.finditer(pattern, tex):
        start = authorship_match.start()
        end = authorship_match.end()
        if _is_enclosed_cmd(envs, start, end) or _is_enclosed_cmd(cmds, start, end):
            continue

        cmd = tex[start:end]
        if _is_empty_command(cmd):
            continue

        cmds.append({
            "start_pos": start,
            "end_pos": end,
            "text": tex[start:end]
        })

    return cmds


def _extract_authorship_cmds_from_tex(tex: str) -> list[LatexCmd]:
    cmds = _extract_authorship_from_tex(reg_exp.AUTHORSHIP_ENV, tex)
    cmds += _extract_authorship_from_tex(reg_exp.AUTHORSHIP, tex, envs=cmds)
    return [LatexCmd(cmd["text"], latex.sanitize_latex_cmd(cmd["text"])) for cmd in cmds]


def _extract_documentclass(tex: str) -> str:
    m = regex.search(reg_exp.LATEX_DOCUMENTCLASS, tex)
    if not m:
        return ""

    return m.group(1)[1:-1].strip()


def _extract_authorship_cmds_from_files(paper_tex_dir: Path) -> ExtCmdData:
    cmds = []
    documentclasses = []
    for tex_file in util.get_all_tex_files(paper_tex_dir):
        tex = util.read(tex_file)
        if tex == "%auto-ignore":
            continue

        tex = latex.remove_comments(tex)
        documentclass = _extract_documentclass(tex)
        if documentclass:
            documentclasses.append(documentclass)

        cmds += _extract_authorship_cmds_from_tex(tex)

    return ExtCmdData(documentclasses, cmds)


def _run_single_element(paper_dir: Path) -> None:
    util.configure_logger(_logger)
    if util.file_exists(paper_dir, util.CMDS_FILE):
        _logger.debug("Commands file already exists for '%s'.", paper_dir.name)
        return

    paper_tex_dir = util.get_paper_tex_dir_by_path(paper_dir)
    if not (ext_cmds := _extract_authorship_cmds_from_files(paper_tex_dir)):
        _logger.debug("No commands found in tex files of '%s'!", paper_dir.name)
        return

    if len(ext_cmds.cmds) > 0 or len(ext_cmds.documentclasses) > 0:
        util.write_obj_to_json(paper_dir, util.CMDS_FILE, ext_cmds)


def run(paper_dirs: list[Path]) -> None:
    """
    Extract LaTeX commands from TeX files that are known to be related to author definitions.
    """
    threaded_run.run(paper_dirs, _run_single_element)
