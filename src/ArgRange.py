import argparse


class ArgRange(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, const=None, default=None, type=None, choices=None,
                 required=False, help=None, metavar=None, **kwargs):
        if "min" not in kwargs and "max" not in kwargs:
            raise ValueError("min or max must be specified")

        self.__min__ = kwargs.pop("min") if "min" in kwargs else None
        self.__max__ = kwargs.pop("max") if "max" in kwargs else None
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        value = int(values)
        if self.__min__ and value < self.__min__:
            value = self.__min__
            print(f"Value of argument '{option_string}' is too small! Changing {values} to {self.__min__}.")

        if self.__max__ and value > self.__max__:
            value = self.__max__
            print(f"Value of argument '{option_string}' is too big! Changed {values} to {self.__max__}.")

        setattr(namespace, self.dest, value)
