# projgen/__init__.py
"""
projgen
=======
A CLI tool to scaffold project directory structures from JSON or YAML files.

Quick start
-----------
>>> from projgen.core import load_config, create_project
>>> data = load_config("my_structure.json")
>>> create_project(data)
PosixPath('/home/user/my_project')
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("projgen")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]