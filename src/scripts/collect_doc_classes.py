"""
Get all extracted document classes and order them by their number of occurrences.
"""

import util


def main():
    classes = {}
    for paper_dir in util.get_paper_dirs():
        if not (ext_cmds := util.read_json(paper_dir, util.CMDS_FILE)):
            continue

        doc_classes = ext_cmds.documentclasses
        for doc_class in doc_classes:
            if doc_class in classes:
                classes[doc_class] += 1
            else:
                classes[doc_class] = 1

    # sort the output by value
    print(f"Found {len(classes)} different classes: {dict(sorted(classes.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()
