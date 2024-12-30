import pathlib

# enables importing everything from a package like `from definiton.multi_cmd_scheme import *`
_TO_IGNORE = [
    "__init__.py"
]
package_path = pathlib.Path(__file__).parent
modules = [f for f in package_path.iterdir() if f.is_file() and f.name.endswith(".py")]
__all__ = [m.name[:-3] for m in modules if m.name not in _TO_IGNORE]
