import difflib
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Literal, Optional, Union

from pygic.config import AUTHOR, ROOT_DIR, TOPTAL_REPO_URL, VERSION
from pygic.file import File, FileType

logger = logging.getLogger(__name__)

TEMPLATES_LOCAL_DIR = ROOT_DIR / "src/pygic/templates"
"""The directory (absolute path) of the pre-downloaded gitignore templates from the toptal/gitignore repository."""

try:
    import appdirs  # type: ignore

    # We use this intermediate variable to have docstring typing on the CLONED_TOPTAL_DIR variable
    __CLONED_TOPTAL_DIR: Optional[Path] = Path(
        appdirs.user_data_dir("pygic", AUTHOR, VERSION)
    )

except ModuleNotFoundError:
    logger.info(
        "`appdirs` is not installed, cloning with git won't be available. "
        "If you want this feature, install `pygic` with the [git] extra or the [dulwich] extra."
    )
    __CLONED_TOPTAL_DIR: Optional[Path] = None

CLONED_TOPTAL_DIR: Optional[Path] = __CLONED_TOPTAL_DIR
"""The directory (absolute path) of the cloned toptal/gitignore repository.
None if `pygic` was not installed with the [git] extra."""


class Templates:
    """Class to manage the gitignore templates.

    The templates are stored in the `directory` directory.
    The directory should contain the following files:
    - `order`: A file that contains the order of the gitignore templates.
        The order is used when creating a gitignore file with multiple templates.
        The order is determined by the line number in the file, starting from 0.
        Empty lines and comments are ignored.
        If a template is not found in the `order` file, it is placed after the ones that are.
    - `*.gitignore`: The gitignore templates. (see `FileType` for more information)
    - `*.patch`: The patches for the gitignore templates.
    - `*.stack`: The stacks for the gitignore templates.

    Files with the same name but different extensions are considered to be part of the same template,
    regardless of the case of the name.

    This class provides 4 main functionalities:
    - `list_template_names()`: List the names of the available templates.
    - `create_one_gitignore(name)`: Create a gitignore file from a single template.
    - `create_gitignore(*names)`: Create a gitignore file from multiple templates.
    - `search_and_create()`: Search for templates and create a gitignore file from the selected ones.

    Attributes:
        directory (Path): The directory containing the gitignore templates.
            Defaults to `TEMPLATES_LOCAL_DIR` which is the directory of the locally downloaded templates
            from the toptal/gitignore repository, without needing to clone the repository.
    """

    def __init__(
        self,
        directory: Optional[Union[str, Path]] = None,
        *,
        clone_directory: Optional[Union[str, Path, Literal["default"]]] = None,
        force_clone: bool = False,
        ignore_num_files_check: bool = False,
    ) -> None:
        """Initialize the `Templates` class.

        The `directory` and `clone_directory` arguments are mutually exclusive.
        If both are provided, `directory` is used and `clone_directory` is ignored.
        If both are None, the default local templates are used.

        Args:
            directory (Optional[Union[str, Path]]): The directory containing the gitignore templates.
                Defaults to None.
                If provided, the directory should contain the gitignore templates.
            clone_directory (Optional[Union[str, Path, Literal["default"]]): The directory to clone the
                toptal/gitignore repository to.
                If "default", the default directory is determined via the `appdirs` library that provides
                a cross-platform user-specific directory for data storage.
                Defaults to None.
            force_clone (bool): If True, in the case where you use the cloned toptal/gitignore repository,
                it is cloned again even if it is already cloned, erasing the previous one.
                Defaults to False.
            ignore_num_files_check (bool): If True, the number of files in the directory is not checked
                when checking the validity of the directory. Otherwise, the directory should contain at least
                500 files when it is not empty.
                Defaults to False.

        Raises:
            ValueError: If `directory` is provided and is not a valid directory.
            ModuleNotFoundError: If `clone_directory` is provided but `pygic` was not installed with the [git] extra
                nor the [dulwich] extra.
            ModuleNotFoundError: If `clone_directory` is provided but `git` is not installed while `pygic` was not
                installed with the [dulwich] extra.
            FileNotFoundError: If the `order` file does not exist in the chosen directory.
            ValueError: If a file in the directory is not a valid template file.
            ValueError: If the directory does not contain at least 500 files when `ignore_num_files_check` is False
                and the directory is not empty. (The directory can be empty or not exist in the case where we want
                to clone the toptal/gitignore repository.)
        """
        if directory is not None:
            # If both `directory` and `clone_directory` are provided, use `directory`
            if clone_directory is not None:
                logger.warning(
                    f"Both `directory` and `clone_directory` are provided. "
                    f"Using `directory`='{directory}' and ignoring `clone_directory`='{clone_directory}'."
                )

            chosen_directory = Path(directory)
            check_directory_existence_and_validity(
                chosen_directory, ignore_num_files=ignore_num_files_check
            )
            cloning = False

        else:
            if clone_directory is not None:
                # If the user wants to clone the toptal/gitignore repository
                # we need to check if the [git] extra or the [dulwich] extra was installed
                if CLONED_TOPTAL_DIR is None:
                    raise ModuleNotFoundError(
                        "`pygic` was not installed with the [git] extra nor the [dulwich] extra, "
                        "so it is not possible to clone the toptal/gitignore repository."
                    )

                # Use the default directory if the user requested it
                if clone_directory == "default":
                    clone_directory = CLONED_TOPTAL_DIR

                chosen_directory = Path(clone_directory)
                # We will try to clone the toptal/gitignore repository
                # if it is not cloned yet or if `force_clone` is True
                dir_validity = check_directory_existence_and_validity(
                    chosen_directory,
                    ignore_num_files=ignore_num_files_check,
                    raise_if_not_exist_or_empty=False,
                )
                if dir_validity:
                    if not force_clone:
                        logger.info(
                            f"Using the already cloned toptal/gitignore repository: {chosen_directory}"
                        )
                    else:
                        logger.info(
                            f"Re-cloning the toptal/gitignore repository to: {chosen_directory}"
                        )
                else:
                    logger.info(
                        f"Cloning the toptal/gitignore repository to: {chosen_directory}"
                    )
                cloning = (not dir_validity) or force_clone
            else:
                # If both `directory` and `clone_directory` are None, use the local templates.
                # No need to check the existence or validity of the default directory here
                # since it is done in the tests.
                chosen_directory = TEMPLATES_LOCAL_DIR
                cloning = False

        self.directory = chosen_directory
        if cloning:
            self.__clone_toptal_gitignore()

    def __clone_toptal_gitignore(self) -> None:
        """Clone the toptal/gitignore repository to the `self.directory` directory
        and update the directory to where the templates are: i.e. `self.directory / "templates"`.

        If `self.directory` already exists, it is erased and the repository is cloned again.

        A spinner is shown while cloning the repository.

        Raises:
            ModuleNotFoundError: If `pygic` was not installed with the [git] extra nor the [dulwich] extra,
                so it is not possible to clone the toptal/gitignore repository.
            ModuleNotFoundError: If `git` is not installed while `pygic` was installed with the [git] extra
                and not the [dulwich] extra.
            FileNotFoundError: If the `order` file does not exist in the cloned directory.
            ValueError: If a file in the directory is not a valid template file.
            ValueError: If the directory does not contain at least 500 files.
        """
        try:
            from yaspin import yaspin  # type: ignore
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "`pygic` was not installed with the [git] extra nor the [dulwich] extra, "
                "so it is not possible to clone the toptal/gitignore repository."
            ) from e

        # If the directory already exists, we erase it
        if self.directory.exists():
            shutil.rmtree(self.directory)
        self.directory.mkdir(exist_ok=True)

        # Clone the toptal/gitignore repository while showing a spinner
        cloning_success = False
        with yaspin(
            text="Cloning repository...", color="yellow", side="right"
        ) as spinner:
            # Check if git is installed
            is_git_installed = True
            is_gitpython_installed = True
            try:
                from git import Repo  # type: ignore

                Repo.clone_from(TOPTAL_REPO_URL, self.directory)
                cloning_success = True

            except ModuleNotFoundError:
                # If the gitpython module is not installed, we pass and try to import dulwich
                is_gitpython_installed = False

            except ImportError as e:
                if "Bad git executable." not in e.msg:
                    # Here we only expect the error to be about git not being installed
                    # Otherwise, we raise it
                    raise e
                else:
                    is_git_installed = False

            if not cloning_success:
                try:
                    from dulwich import porcelain  # type: ignore

                    porcelain.clone(TOPTAL_REPO_URL, self.directory)

                except ModuleNotFoundError as e:
                    if is_gitpython_installed:
                        if not is_git_installed:
                            raise ModuleNotFoundError(
                                "`pygic` was installed with the [git] extra but not the [dulwich] extra, "
                                "but `git` is not installed. The GitPython library requires git to be installed. "
                                "If you don't want to install `git`, you can install `pygic` with the [dulwich] extra "
                                "instead of the [git] extra. Otherwise, please install `git` to allow `pygic` "
                                "to clone the toptal/gitignore repository, or please use the local templates."
                            ) from e
                        else:
                            raise RuntimeError(
                                "GitPython and Git are installed but the cloning was unsuccessful and no errors were raised before. "
                                "This should not happen."
                            ) from e
                    raise ModuleNotFoundError(
                        "`pygic` was not installed with the [git] extra nor the [dulwich] extra, "
                        "so it is not possible to clone the toptal/gitignore repository."
                    ) from e

            spinner.text = "Repository cloned"
            spinner.ok("✅")

        # Update the directory to where the templates are
        self.directory = self.directory / "templates"

        # And check the validity of the directory
        check_directory_existence_and_validity(self.directory)

    def __get_order_dict(self) -> DefaultDict[str, Union[int, float]]:
        """Get the order of the gitignore templates.

        The order is used when creating a gitignore file with multiple templates.
        The order is determined by the line number in the file, starting from 0.
        Empty lines and comments are ignored.
        If a template is not found in the `order` file, its priority is set to `float("inf")`.

        Returns:
            DefaultDict[str, Union[int, float]]: A dictionary with the template names as keys (lowercase)
                and their order index as values.

        Raises:
            FileNotFoundError: If the `order` file does not exist.
            ValueError: If there is a duplicate template name in the `order` file.
        """
        # Open the `order` file
        order_file = self.directory / "order"
        if not order_file.exists():
            raise FileNotFoundError(f"File '{order_file}' does not exist.")

        order_dict: DefaultDict[str, Union[int, float]] = defaultdict(
            lambda: float("inf")
        )
        with open(order_file, "r") as f:
            order_idx = 0
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name = line.lower()
                if name in order_dict:
                    raise ValueError(
                        f"Duplicate template name '{name}' found in the 'order' file."
                    )
                order_dict[name] = order_idx
                order_idx += 1

        return order_dict

    def list_template_names(self) -> List[str]:
        """List the names of the available templates, sorted alphabetically."""
        return sorted([file.stem for file in self.directory.glob("*.gitignore")])

    def create_one_gitignore(self, name: str) -> str:
        """Create a gitignore file from a single template.

        The methodology is as follows:
        - Find the files that start with the name (case-insensitive).
        - If no file is found, find the closest match and suggest it to the user.
        - Compile the gitignore file from the found files:
            - The `gitignore` file is added first, with the header: `### {name} ###`.
            - Then the `patch` file is added, with the header: `### {name} Patch ###`.
            - Then all the `stack` files are added if nay, with the headers: `### {name}.{stack_name} Stack ###`.
            - Finally, the content is joined and duplicated lines are removed.

        NOTE: There might be a bug in the toptal/gitignore repository since, sometimes, there exist
              patch files that should be extensions of regular gitignores but are not included.
              For example, for `Rider`, there is a `Rider.gitignore` file, and also a `Rider+all.patch`
              and a `Rider+iml.patch`, but no `Rider+all.gitignore` or `Rider+iml.gitignore` files.
              Thus, the `Rider+all.patch` and `Rider+iml.patch` can never be included in any gitignores.
              Sometimes, there are associated gitignore files for such cases like `Jetbrains+all.gitignore`
              to actually implement this feature. The goal of this project is not to correct the templates
              from toptal.gitignore so this bug won't be fixed until they fix it themselves.

        Args:
            name (str): The name of the gitignore template to use.

        Returns:
            str: The content of the gitignore file.

        Raises:
            FileNotFoundError: If no template is found for the provided name.
        """
        lower_name = name.lower()
        # Glob the files that start with the name
        # Example:
        # - name = reactnative
        # - Globbed:
        #   - ReactNative.gitignore
        #   - ReactNative.patch  (does not actually exist)
        #   - ReactNative.Linux.stack
        # - Ignored:
        #   - ReactNative+all.patch  (does not actually exist)
        file_paths = [
            file
            for file in self.directory.glob("*.*")
            if file.stem.lower().split(".")[0] == lower_name
        ]
        if not file_paths:
            # Get all possible template names
            all_files = [
                file.stem.lower() for file in self.directory.glob("*.gitignore")
            ]
            # Find the closest match
            closest_matches = difflib.get_close_matches(name, all_files)
            if closest_matches:
                suggestion = closest_matches[0]
                raise FileNotFoundError(
                    f"No template found for '{name}' regardless of case. Did you mean '{suggestion}'?"
                )
            else:
                raise FileNotFoundError(
                    f"No template found for '{name}' regardless of case."
                )

        # We use List[File] and not just one File to account for the case when there are multiple patches
        # Example: ReactNative.Android.stack, ReactNative.Linux.stack, etc.
        files: DefaultDict[FileType, List[File]] = defaultdict(list)
        for file_path in file_paths:
            file = File(file_path)
            files[file.type].append(file)

        # Sort the lists alphabetically
        # NOTE: The `lower` is important to sort case-insensitively
        # Otherwise, for exampe, Z is before a in the ASCII table
        for file_type in files:
            files[file_type] = sorted(
                files[file_type], key=lambda file: file.name.lower()
            )

        gitignore = []  # Stores the lines for the final string
        if "gitignore" in files:
            for file in files["gitignore"]:
                gitignore.append(f"### {file.name} ###")
                gitignore.append(file.get_content())
        if "patch" in files:
            for file in files["patch"]:
                gitignore.append(f"### {file.name} Patch ###")
                gitignore.append(file.get_content())
        if "stack" in files:
            for file in files["stack"]:
                gitignore.append(f"### {file.name} Stack ###")
                gitignore.append(file.get_content())

        gitignore = "\n".join(gitignore)
        gitignore = remove_duplicated_lines(gitignore)
        return gitignore

    def create_gitignore(self, *names: str) -> str:
        """Create a gitignore file from multiple templates.

        The methodology is as follows:
        - Get the order of the gitignore templates.
        - Create the gitignore files from the provided names.
        - Sort the gitignore names based on their order index.
        - Compile the gitignores in the sorted order.
        - Remove duplicated lines from the final gitignore file.

        Args:
            *names (str): The names of the gitignore templates to use.

        Returns:
            str: The content of the gitignore file.

        Raises:
            ValueError: If no template is provided.
            FileNotFoundError: If no template is found for a provided name.
        """
        if not names:
            raise ValueError(
                "You need to provide at least one template for a gitignore to be generated."
            )

        # Get the order of the gitignore templates
        order_dict: DefaultDict[str, Union[int, float]] = self.__get_order_dict()
        sub_gitignores_dict: Dict[str, str] = {
            name.lower(): self.create_one_gitignore(name) for name in names
        }

        # Sort the gitignore names based on their order index
        sorted_names = sorted(
            sub_gitignores_dict.keys(), key=lambda name: order_dict[name]
        )

        # Compile the gitignores in the sorted order
        gitignore = "\n\n".join(sub_gitignores_dict[name] for name in sorted_names)

        gitignore = remove_duplicated_lines(gitignore)
        return gitignore

    def __search_names(self) -> List[str]:
        """Search for templates and return the selected names.

        `pzp` is used to search for the templates.
        The user can select multiple templates by pressing Enter on the selected item.
        The search stops when the user presses ESC, CTRL-C, CTRL-G, or CTRL-Q.

        Returns:
            List[str]: The selected names.

        Raises:
            ModuleNotFoundError: If `pygic` was not installed with the [search] extra,
        """
        try:
            from pzp import pzp  # type: ignore
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "`pygic` was not installed with the [search] extra, "
                "so it is not possible to search for templates."
            ) from e

        candidates = self.list_template_names()
        selected_names: List[str] = []

        while True:
            name = pzp(
                candidates=candidates,
                fullscreen=False,
                height=20,
                header_str=(
                    f"To stop searching, press ESC, CTRL-C, CTRL-G, or CTRL-Q\n"
                    f"Already selected items: {selected_names}"
                ),
            )
            if name is None:
                break
            selected_names.append(name)

        return selected_names

    def search_and_create(self) -> str:
        """Search for templates and create a gitignore file from the selected ones.

        `pzp` is used to search for the templates.
        The user can select multiple templates by pressing Enter on the selected item.
        The search stops when the user presses ESC, CTRL-C, CTRL-G, or CTRL-Q.

        Returns:
            str: The content of the gitignore file.

        Raises:
            ModuleNotFoundError: If `pygic` was not installed with the [search] extra,
            ValueError: If no template is selected.
        """
        selected_names = self.__search_names()
        if not selected_names:
            raise ValueError(
                "You need to select at least one template for a gitignore to be generated."
            )
        return self.create_gitignore(*selected_names)


def check_directory_existence_and_validity(
    directory: Path,
    *,
    ignore_num_files: bool = False,
    raise_if_not_exist_or_empty: bool = True,
) -> bool:
    """Check if the directory is valid for the `Templates` class.

    The directory should only contain the following files:
    - `order`: A file that contains the order of the gitignore templates.
    - `*.gitignore`: The gitignore templates. (see `FileType` for more information)
    - `*.patch`: The patches for the gitignore templates.
    - `*.stack`: The stacks for the gitignore templates.

    The actual local copy of the toptal/gitignore repository contains more than 500 files,
    so this function also checks that the provided directory contains at least 500 files
    if `ignore_num_files` is False.

    Args:
        directory (Path): The directory to check.
        ignore_num_files (bool): If True, the function will not check the number of files in the directory.
            Defaults to False.
        raise_if_not_exist_or_empty (bool): If True, the function raises an error if the directory does not exist
            or is empty. Otherwise, it returns False. Defaults to True.

    Returns:
        bool: True if the directory is valid, False if it does not exist or is empty, and `raise_if_not_exist_or_empty`
            is False. Otherwise, it raises an error.

    Raises:
        NotADirectoryError: If the `directory` is not a directory.
        FileNotFoundError: If the `order` file does not exist.
        ValueError: If a file in the directory is not a valid template file.
        ValueError: If the directory does not contain at least 500 files when `ignore_num_files` is False
            and the directory is not empty.
    """

    def __check_directory_existence_and_validity(
        directory: Path,
        *,
        ignore_num_files: bool = False,
    ) -> bool:
        if not directory.exists():
            return False

        if not directory.is_dir():
            raise NotADirectoryError(f"'{directory}' is not a directory.")

        # Check if the directory is empty
        if not any(directory.iterdir()):
            return False

        # Otherwise, we consider that the directory should be valid and check everything else
        # Check if the `order` file exists
        order_file = directory / "order"
        if not order_file.exists():
            raise FileNotFoundError(f"File '{order_file}' does not exist.")

        # Check if the files in the directory are valid template files
        file_paths = list(directory.glob("*.*"))
        for file_path in file_paths:
            if file_path.suffix[1:] not in FileType.values():
                raise ValueError(
                    f"File '{file_path}' is not a valid template file. "
                    f"Only the following extensions are allowed: {', '.join(FileType.values())}"
                )

        if not ignore_num_files:
            # Check if the directory contains at least 500 files
            num_files = len(file_paths)
            if num_files < 500:
                raise ValueError(
                    f"The directory '{directory}' should contain at least 500 files, "
                    f"but it only contains {num_files} files."
                )

        return True

    directory_validity = __check_directory_existence_and_validity(
        directory, ignore_num_files=ignore_num_files
    )
    if not directory_validity and raise_if_not_exist_or_empty:
        raise FileNotFoundError(f"Directory '{directory}' does not exist or is empty.")

    return directory_validity


def remove_duplicated_lines(content: str) -> str:
    """Remove duplicate lines while preserving empty lines and comments.

    Processes a string content line by line, keeping track of unique non-empty,
    non-comment lines. Empty lines and comments are always preserved in their
    original position.

    The first occurrence of all duplicate lines is the one that is kept.

    Args:
        content (str): A string containing multiple lines of text.

    Returns:
        str: The processed string with duplicate lines removed.

    Example:
        >>> text = "# Header\\nline1\\n\\nline1\\n# Comment\\nline2"
        >>> remove_duplicated_lines(text)
        '# Header\\nline1\\n\\n# Comment\\nline2'
    """
    seen = set()
    result = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            result.append(line)
            continue
        if stripped not in seen:
            seen.add(stripped)
            result.append(line)

    # Adjust the number of newlines at the end of the content
    # to match the original content
    if content.endswith("\n"):
        result.append("")

    return "\n".join(result)
