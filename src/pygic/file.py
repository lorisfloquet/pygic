from enum import Enum
from pathlib import Path
from typing import List


class FileType(str, Enum):
    """Enum to represent the type of a template file."""

    GITIGNORE = "gitignore"
    """A .gitignore file is the foundation of all templates.
    Each .gitignore file contains gitignore information related to the title of the file.
    For example, Python.gitignore contains a gitignore template that is used when creating a
    project in Python.
    """

    PATCH = "patch"
    """A .patch is a file to extend the functionality of a template.
    The source for some of the template files on toptal/gitignore come from github/gitignore.
    GitHub maintains strict contributing guidelines and the .patch file allows anyone to extend any
    of the templates to add extra template rules.
    """

    STACK = "stack"
    """A .stack is a file that allows for the creation of code stacks (LAMP, MEAN, React Native).
    In today's development environment a .gitignore file is usually comprised of multiple technologies.
    A stack creates an elegant way to keep the stack up to date with child dependencies.
    """

    @classmethod
    def values(cls) -> List[str]:
        """Get the possible FileType values as a list of strings."""
        return [item.value for item in cls]


class File:
    """A gitignore file.

    Can be of type: `gitignore`, `patch`, or `stack`. (see `FileType` for more information)

    Attributes:
        path (Path): The path to the file. If the file is a symlink, the path is resolved.
        type (FileType): The type of the file.
        name (str): The name of the file without the extension.
            Example: `Python` for `Python.gitignore`.
    """

    def __init__(self, path: Path) -> None:
        # Ensure that the path is a Path object and check if the file exists
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"File '{self.path}' does not exist.")

        # Get the type of the file and check if it is supported
        self.type = FileType(self.path.suffix[1:])

        # Extract the name of the file
        self.name = self.path.stem

        # Finally, resolve the path if it is a symlink
        if self.path.is_symlink():
            self.path = self.path.resolve()

    def get_content(self) -> str:
        """Get the content of the file as a string.

        NOTE: The content is not stored in memory, so the file is read every time this method is called.
            This is the wanted behavior since `pygic` is a CLI tool and the templates are not expected to be
            read multiple times in a single run.
        """
        with open(self.path, "r") as f:
            content = f.read()
        return content
