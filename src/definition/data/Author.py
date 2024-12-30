from dataclasses import dataclass


@dataclass
class Author:
    name: str
    affiliations: list[str]

    def __eq__(self, other):
        if not isinstance(other, Author):
            return NotImplemented

        if self.name != other.name:
            return False

        if len(self.affiliations) != len(other.affiliations):
            return False

        for affiliation in self.affiliations:
            if affiliation not in other.affiliations:
                return False

        return True
