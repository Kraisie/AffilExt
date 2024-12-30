from dataclasses import dataclass


@dataclass
class ResearchLocation:
    location_name: str
    country_name: str


@dataclass
class ResearchOrganization:
    ror_id: str
    names: list[str]
    locations: list[ResearchLocation]

    def get_ror_id(self):
        # get only the ID part: https://ror.org/id
        # remove "/" at the end to make sure, should not happen
        return self.ror_id.rstrip("/").split("/")[-1]

    # __eq__ and __hash__ so we can use set[ResearchOrganization]
    def __eq__(self, other):
        if other is None:
            return False

        if not isinstance(other, ResearchOrganization):
            return False

        return self.ror_id == other.ror_id

    def __hash__(self):
        return hash(self.ror_id)


@dataclass
class RorDataset:
    src_file_name: str
    data: list[ResearchOrganization]
