from abc import abstractmethod, ABCMeta

from definition.data.Author import Author


# this is primarily to provide an easy way to get all schemes by using MultiCmdScheme.__subclasses__().
# thus avoiding to use dynamic importing via importlib (the former way how we achieved this).
# of course that's not optimal.
class MultiCmdScheme(metaclass=ABCMeta):

    @abstractmethod
    def validate(self, cmds: list[str]) -> bool:
        pass

    @abstractmethod
    def extract(self, cmds: list[str]) -> list[Author]:
        pass
