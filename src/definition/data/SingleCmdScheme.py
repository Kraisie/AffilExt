from abc import abstractmethod, ABCMeta

from definition.data.Author import Author


# this is primarily to provide an easy way to get all schemes by using SingleCmdScheme.__subclasses__().
# thus avoiding to use dynamic importing via importlib (the former way how we achieved this).
# of course that's not optimal.
class SingleCmdScheme(metaclass=ABCMeta):

    @abstractmethod
    def validate(self, cmd_name: str, cmd_content: str) -> bool:
        pass

    @abstractmethod
    def extract(self, cmd_name: str, cmd_content: str) -> list[Author]:
        pass
