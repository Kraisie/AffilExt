"""
Regenerate the skip list ^^
"""

import util

paper_dirs = util.get_paper_dirs()
run = 0

to_skip = set()

for paper_dir in paper_dirs:
    if len(util.get_all_files_recursive(paper_dir / "tex", ".tex")) > 0:
        continue

    to_skip.add(paper_dir.name.replace("_", "/"))

util.write_obj_to_json(util.get_papers_dir(), util.SKIPPED_DL_FILE, list(to_skip))
print(f"Found {len(to_skip)} papers to skip.")
