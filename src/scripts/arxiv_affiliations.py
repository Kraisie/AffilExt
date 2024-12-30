"""
Get all affiliation from the ArXiv metadata.
"""
import util
from definition.data.ArxivMetadata import ArxivMetadata


def main():
    affs = []
    papers_with_full_affiliation = 0
    papers_with_partial_affiliation = 0
    for paper_dir in util.get_paper_dirs():
        arxiv_metadata: ArxivMetadata = util.read_json(paper_dir, util.ARXIV_METADATA_FILE)
        authors = arxiv_metadata.authors
        all_authors_have_affiliation = True
        for author in authors:
            affiliations = author.affiliations
            if len(affiliations) == 0:
                all_authors_have_affiliation = False
            else:
                papers_with_partial_affiliation += 1
                for affiliation in affiliations:
                    affs.append(affiliation)

        if all_authors_have_affiliation:
            papers_with_full_affiliation += 1

    print(f"Found {papers_with_full_affiliation} papers with each author having an affiliation.")
    print(f"Found {papers_with_partial_affiliation} papers with only some author(s) having an affiliation")
    print(f"Found {len(affs)} affiliations in ArXiv metadata.")
    # print(f"\n{affs}")


if __name__ == '__main__':
    main()
