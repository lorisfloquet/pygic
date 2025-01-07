import logging
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pytest

from pygic.config import ROOT_DIR, TOPTAL_REPO_URL
from pygic.gitignore import (
    TEMPLATES_LOCAL_DIR,
    Gitignore,
    check_directory_existence_and_validity,
    remove_duplicated_lines,
)


@pytest.fixture
def mock_modules():
    """Fixture to mock sys.module to ensure"""

    original_modules = sys.modules.copy()
    yield
    sys.modules.clear()
    sys.modules.update(original_modules)


#######################################################################################
# Test the Gitignore class
#######################################################################################


class TestGitignore:
    """Test suite for the Gitignore class."""

    def test__init__default(self):
        templates = Gitignore()
        assert templates.directory == TEMPLATES_LOCAL_DIR

    def test__init__valid_directory(self):
        templates = Gitignore(directory=TEMPLATES_LOCAL_DIR)
        assert templates.directory == TEMPLATES_LOCAL_DIR

    def test__init__valid_directory_plus_clone(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.WARNING):
            templates = Gitignore(
                directory=TEMPLATES_LOCAL_DIR, clone_directory=Path("non_existent")
            )
            assert templates.directory == TEMPLATES_LOCAL_DIR
            assert (
                "Both `directory` and `clone_directory` are provided. " in caplog.text
            )

    def test__init__invalid_directory(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="does not exist or is empty."):
            Gitignore(directory=tmp_path / "non_existent")

    def test__init__clone_no_git(self, tmp_path: Path):
        # By mocking CLONED_TOPTAL_DIR to None, the program will think that neither
        # GitPython nor Dulwich is installed
        with patch("pygic.gitignore.CLONED_TOPTAL_DIR", None):
            with pytest.raises(
                ModuleNotFoundError,
                match="so it is not possible to clone the toptal/gitignore repository.",
            ):
                Gitignore(clone_directory=tmp_path)

    def test__init__clone_default_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ):
        with (
            caplog.at_level(logging.INFO),
            patch("pygic.gitignore.CLONED_TOPTAL_DIR", tmp_path / "empty"),
            patch(
                "pygic.gitignore.Gitignore._Gitignore__clone_toptal_gitignore",
                return_value=None,
            ) as mock_clone_toptal,
        ):
            # Ensure that the directory is empty
            shutil.rmtree(tmp_path / "empty", ignore_errors=True)

            Gitignore(clone_directory="default")

            # Check the info message
            assert (
                f"Cloning the toptal/gitignore repository to: {tmp_path / 'empty'}"
                in caplog.text
            )

            # Assert that the __clone_toptal_gitignore method was called
            mock_clone_toptal.assert_called_once()

    @pytest.mark.usefixtures("mock_modules")
    def test__init__clone_nested_directories(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ):
        nested_dir = tmp_path / "some" / "nested" / "path"
        # Mock CLONED_TOPTAL_DIR to the nested directory
        # Mock Repo.clone_from to do nothing
        # Mock check_directory_existence_and_validity to return True
        with (
            caplog.at_level(logging.INFO),
            patch("pygic.gitignore.CLONED_TOPTAL_DIR", nested_dir),
            patch("git.Repo.clone_from", return_value=None),
            patch(
                "pygic.gitignore.check_directory_existence_and_validity",
                return_value=False,
            ),
        ):
            # Ensure that the directory is empty
            shutil.rmtree(tmp_path / "some", ignore_errors=True)

            Gitignore(clone_directory="default")

            # Check the info message
            assert (
                f"Cloning the toptal/gitignore repository to: {nested_dir}"
                in caplog.text
            )

    def test__init__clone_already_cloned(self, caplog: pytest.LogCaptureFixture):
        with (
            caplog.at_level(logging.INFO),
            patch(
                "pygic.gitignore.Gitignore._Gitignore__clone_toptal_gitignore",
                return_value=None,
            ) as mock_clone_toptal,
        ):
            Gitignore(clone_directory=TEMPLATES_LOCAL_DIR)

            # Check the info message
            assert (
                f"Using the already cloned toptal/gitignore repository: {TEMPLATES_LOCAL_DIR}"
                in caplog.text
            )

            # Assert that the __clone_toptal_gitignore method was not called
            mock_clone_toptal.assert_not_called()

    def test__init__clone_already_cloned_force(self, caplog: pytest.LogCaptureFixture):
        with (
            caplog.at_level(logging.INFO),
            patch(
                "pygic.gitignore.Gitignore._Gitignore__clone_toptal_gitignore",
                return_value=None,
            ) as mock_clone_toptal,
        ):
            Gitignore(clone_directory=TEMPLATES_LOCAL_DIR, force_clone=True)

            # Check the info message
            assert (
                f"Re-cloning the toptal/gitignore repository to: {TEMPLATES_LOCAL_DIR}"
                in caplog.text
            )

            # Assert that the __clone_toptal_gitignore method was called
            mock_clone_toptal.assert_called_once()

    @staticmethod
    def setup_templates(path: Path) -> Gitignore:
        """Create a Gitignore instance with the given path.

        Cloning won't be called because the clone_directory is not empty
        and ignore_num_files_check is True.
        """
        # Add the 'order' file
        (path / "order").touch()
        return Gitignore(clone_directory=path, ignore_num_files_check=True)

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_success_gitpython(self, tmp_path: Path):
        """Test that the repository is cloned successfully using GitPython."""
        templates = self.setup_templates(tmp_path)

        # Mock Repo.clone_from to do nothing
        # Mock check_directory_existence_and_validity to return True
        with (
            patch("git.Repo.clone_from", return_value=None) as mock_clone,
            patch(
                "pygic.gitignore.check_directory_existence_and_validity",
                return_value=True,
            ),
        ):
            # Call the method
            templates._Gitignore__clone_toptal_gitignore()

            # Assert that the directory was updated
            assert templates.directory == tmp_path / "templates"

            # Assert that Repo.clone_from was called
            # We check with the parent directory because it was updated in the method
            mock_clone.assert_called_once_with(
                TOPTAL_REPO_URL, templates.directory.parent
            )

            # Assert that nothing was cloned since we mocked Repo.clone_from
            assert not (tmp_path / "templates").exists()

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_success_dulwich(self, tmp_path: Path):
        """Test that the repository is cloned successfully using Dulwich when GitPython is not available."""
        templates = self.setup_templates(tmp_path)

        # Simulate that GitPython is not installed
        # Mock porcelain.clone to do nothing
        # Mock check_directory_existence_and_validity to return True
        with (
            patch.dict(sys.modules, {"git": None}),
            patch("dulwich.porcelain.clone", return_value=None) as mock_clone,
            patch(
                "pygic.gitignore.check_directory_existence_and_validity",
                return_value=True,
            ),
        ):
            # Call the method
            templates._Gitignore__clone_toptal_gitignore()

            # Assert that the directory was updated
            assert templates.directory == tmp_path / "templates"

            # Assert that porcelain.clone was called
            mock_clone.assert_called_once_with(
                TOPTAL_REPO_URL, templates.directory.parent
            )

            # Assert that nothing was cloned since we mocked porcelain.clone
            assert not (tmp_path / "templates").exists()

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_no_gitpython_no_dulwich(self, tmp_path: Path):
        """Test that a ModuleNotFoundError is raised when neither GitPython nor Dulwich is installed."""
        templates = self.setup_templates(tmp_path)

        # Simulate that both GitPython and Dulwich are not installed
        # Expect ModuleNotFoundError
        with (
            patch.dict(sys.modules, {"git": None, "dulwich": None}),
            pytest.raises(
                ModuleNotFoundError,
                match="so it is not possible to clone the toptal/gitignore repository.",
            ),
        ):
            templates._Gitignore__clone_toptal_gitignore()

        # Assert that nothing was cloned since the method raised an exception
        assert not (tmp_path / "templates").exists()

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_git_not_installed_dulwich_installed(
        self, tmp_path: Path
    ):
        """Test that the repository is cloned using Dulwich when Git is not installed, even if GitPython is installed."""
        templates = self.setup_templates(tmp_path)

        # Hide git from PATH
        # Mock Repo.clone_from to raise ImportError indicating git is not installed
        # Mock check_directory_existence_and_validity to return True
        with (
            patch.dict(os.environ, {"GIT_PYTHON_GIT_EXECUTABLE": "mock_git"}),
            patch("dulwich.porcelain.clone", return_value=None) as mock_clone,
            patch(
                "pygic.gitignore.check_directory_existence_and_validity",
                return_value=True,
            ),
        ):
            # The templates directory is updated after cloning
            templates_old_dir = templates.directory
            templates._Gitignore__clone_toptal_gitignore()

            # Assert that porcelain.clone was called
            mock_clone.assert_called_once_with(TOPTAL_REPO_URL, templates_old_dir)

            # Assert that the directory was updated
            assert templates.directory == tmp_path / "templates"

            # Assert that nothing was cloned since we mocked porcelain.clone
            assert not (tmp_path / "templates").exists()

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_git_not_installed_no_dulwich(self, tmp_path: Path):
        """Test that a ModuleNotFoundError is raised when Git is not installed and Dulwich is not available."""
        templates = self.setup_templates(tmp_path)

        # Hide git from PATH
        # Simulate that Dulwich is not installed
        with (
            patch.dict(os.environ, {"GIT_PYTHON_GIT_EXECUTABLE": "mock_git"}),
            patch.dict(sys.modules, {"dulwich": None}),
            pytest.raises(ModuleNotFoundError, match="but `git` is not installed"),
        ):
            templates._Gitignore__clone_toptal_gitignore()

        # Assert that nothing was cloned since the method raised an exception
        assert not (tmp_path / "templates").exists()

    @pytest.mark.usefixtures("mock_modules")
    def test_clone_toptal_gitignore_directory_exists(self, tmp_path: Path):
        """Test that the existing directory is removed before cloning."""
        templates = self.setup_templates(tmp_path)

        # Create the directory to simulate it already exists
        templates.directory.mkdir(parents=True, exist_ok=True)

        # Mock shutil.rmtree to do nothing
        # Mock Repo.clone_from to do nothing
        # Mock check_directory_existence_and_validity to return True
        with (
            patch("shutil.rmtree") as mock_rmtree,
            patch("git.Repo.clone_from") as mock_clone,
            patch(
                "pygic.gitignore.check_directory_existence_and_validity",
                return_value=True,
            ),
        ):
            # The templates directory is updated after cloning
            templates_old_dir = templates.directory
            templates._Gitignore__clone_toptal_gitignore()

            # Assert that shutil.rmtree was called
            mock_rmtree.assert_called_once_with(templates_old_dir)

            # Assert that Repo.clone_from was called
            mock_clone.assert_called_once_with(TOPTAL_REPO_URL, templates_old_dir)

            # Assert that the directory was updated
            assert templates.directory == tmp_path / "templates"

            # Assert that nothing was cloned since we mocked Repo.clone_from
            assert not (tmp_path / "templates").exists()

    def test_get_order_dict_happy_path(self, tmp_path: Path):
        templates = self.setup_templates(tmp_path)

        # Create an 'order' file with some lines, empty lines, and comments
        order_file_content = """\
# This is a comment
python
node
# Another comment

rust
go
"""
        (tmp_path / "order").write_text(order_file_content)

        order_dict = templates._Gitignore__get_order_dict()

        # Verify that the returned object is a defaultdict with default = 0
        assert isinstance(order_dict, defaultdict)
        assert order_dict.default_factory() == 0

        # Verify the order of each listed template
        # Non-comment, non-empty lines in their appearance order:
        # python -> 0, node -> 1, rust -> 2, go -> 3
        assert order_dict["python"] == 0
        assert order_dict["node"] == 1
        assert order_dict["rust"] == 2
        assert order_dict["go"] == 3

        # 'java' is not found, so it should return 0
        assert order_dict["java"] == 0

    def test_get_order_dict_non_existent_file(self, tmp_path: Path):
        templates = self.setup_templates(tmp_path)
        # Remove the 'order' file to simulate it doesn't exist
        (tmp_path / "order").unlink()
        with pytest.raises(FileNotFoundError):
            templates._Gitignore__get_order_dict()

    def test_get_order_dict_only_comments_and_empty_lines(self, tmp_path: Path):
        templates = self.setup_templates(tmp_path)
        # Create an 'order' file that has no actual templates, only comments and empty lines
        order_file_content = """\
# This is a comment line

# Another comment

"""
        (tmp_path / "order").write_text(order_file_content)

        order_dict = templates._Gitignore__get_order_dict()

        # The dictionary should still be a defaultdict but have no entries
        assert isinstance(order_dict, defaultdict)
        assert len(order_dict) == 0

    def test_get_order_dict_duplicate_entries(self, tmp_path: Path):
        templates = self.setup_templates(tmp_path)
        order_file_content = """\
python
node
python
"""
        (tmp_path / "order").write_text(order_file_content)

        with pytest.raises(
            ValueError,
            match="Duplicate template name 'python' found in the 'order' file.",
        ):
            templates._Gitignore__get_order_dict()

    def test_list_template_names(self):
        templates = Gitignore()
        names = templates.list_template_names()
        assert len(names) > 500
        assert "Python" in names
        assert "Node" in names
        assert "Rust" in names
        assert "Go" in names
        assert "Java" in names
        # Check that the names are sorted
        assert names == sorted(names)

    @pytest.mark.parametrize(
        "file",
        [
            file
            for file in (ROOT_DIR / "tests" / "targets").glob("*.gitignore")
            if "." not in file.stem
        ],
    )
    def test_create_one_gitignore_happy_path(self, file: Path):
        templates = Gitignore()
        with open(file, "r") as f:
            content = f.read()
        gitignore = templates.create_one_gitignore(file.stem)
        assert gitignore == content

    def test_create_one_gitignore_close_match_error(self):
        templates = Gitignore()
        with pytest.raises(
            FileNotFoundError,
            match="No template found for 'pyton' regardless of case. Did you mean 'python'?",
        ):
            templates.create_one_gitignore("pyton")

    def test_create_one_gitignore_no_match_error(self):
        templates = Gitignore()
        with pytest.raises(FileNotFoundError) as exc_info:
            templates.create_one_gitignore("you")
        assert str(exc_info.value) == "No template found for 'you' regardless of case."

    @pytest.mark.parametrize(
        "file",
        (ROOT_DIR / "tests" / "targets").glob("*.gitignore"),
    )
    def test_create_happy_path(self, file: Path):
        templates = Gitignore()
        with open(file, "r") as f:
            content = f.read()
        file_name = file.stem
        if "." in file_name:
            # We split the multiple names by '.' and test each one
            names = file_name.split(".")
            gitignore = templates.create(*names)
        else:
            gitignore = templates.create(file_name)
        assert gitignore == content

    def test_create_one_template_close_match_error(self):
        templates = Gitignore()
        with pytest.raises(
            FileNotFoundError,
            match="No template found for 'pyton' regardless of case. Did you mean 'python'?",
        ):
            templates.create("pyton")

    def test_create_one_template_no_match_error(self):
        templates = Gitignore()
        with pytest.raises(FileNotFoundError) as exc_info:
            templates.create("you")
        assert str(exc_info.value) == "No template found for 'you' regardless of case."

    def test_create_empty_input(self):
        templates = Gitignore()
        with pytest.raises(
            ValueError,
            match="You need to provide at least one template for a gitignore to be generated.",
        ):
            templates.create()


#######################################################################################
# Test the remove_duplicated_lines function
#######################################################################################


def test_remove_duplicated_lines_no_duplicates():
    content = "line1\nline2\nline3"
    expected = "line1\nline2\nline3"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_duplicate_non_comment_lines():
    content = "line1\nline2\nline1\nline3\nline2"
    expected = "line1\nline2\nline3"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_duplicate_comment_lines():
    content = "# comment1\n# comment1\nline1\nline1"
    expected = "# comment1\n# comment1\nline1"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_empty_lines():
    content = "line1\n\nline2\n\nline1"
    expected = "line1\n\nline2\n"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_mixed_content():
    content = "# Header\nline1\n\nline1\n# Comment\nline2\nline2"
    expected = "# Header\nline1\n\n# Comment\nline2"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_leading_trailing_whitespace():
    content = "  line1  \nline1\nline1  \nline2"
    expected = "  line1  \nline2"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_case_sensitivity():
    content = "Line1\nline1\nLINE1"
    expected = "Line1\nline1\nLINE1"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_whitespace_differences():
    content = "line1\nline1 \nline1  \nline1\t"
    expected = "line1"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_only_comments_and_empty_lines():
    content = "# Comment1\n\n# Comment2\n\n\n"
    expected = "# Comment1\n\n# Comment2\n\n\n"
    assert remove_duplicated_lines(content) == expected


def test_remove_duplicated_lines_example_from_docstring():
    content = "# Header\nline1\n\nline1\n# Comment\nline2"
    expected = "# Header\nline1\n\n# Comment\nline2"
    assert remove_duplicated_lines(content) == expected


#######################################################################################
# Test the check_directory_existence_and_validity function
#######################################################################################


def test_check_directory_existence_and_validity_local_dir():
    assert check_directory_existence_and_validity(TEMPLATES_LOCAL_DIR) is True


def test_check_directory_existence_and_validity_empty_directory(tmp_path: Path):
    assert (
        check_directory_existence_and_validity(
            tmp_path, raise_if_not_exist_or_empty=False
        )
        is False
    )


def test_check_directory_existence_and_validity_empty_directory_raise(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="does not exist or is empty."):
        check_directory_existence_and_validity(
            tmp_path, raise_if_not_exist_or_empty=True
        )


def test_check_directory_existence_and_validity_non_existent_directory(tmp_path: Path):
    non_existent_dir = tmp_path / "non_existent"
    assert (
        check_directory_existence_and_validity(
            non_existent_dir, raise_if_not_exist_or_empty=False
        )
        is False
    )


def test_check_directory_existence_and_validity_non_existent_directory_raise(
    tmp_path: Path,
):
    non_existent_dir = tmp_path / "non_existent"
    with pytest.raises(FileNotFoundError, match="does not exist or is empty."):
        check_directory_existence_and_validity(
            non_existent_dir, raise_if_not_exist_or_empty=True
        )


def test_check_directory_existence_and_validity_not_a_directory(tmp_path: Path):
    not_a_directory = tmp_path / "file.txt"
    not_a_directory.touch()
    with pytest.raises(NotADirectoryError):
        check_directory_existence_and_validity(not_a_directory)


def test_check_directory_existence_and_validity_missing_order_file(tmp_path: Path):
    # Create some valid files but no 'order' file
    for i in range(1, 501):
        (tmp_path / f"template{i}.gitignore").touch()
    with pytest.raises(FileNotFoundError) as exc_info:
        check_directory_existence_and_validity(tmp_path)
    assert "order" in str(exc_info.value)


def test_check_directory_existence_and_validity_invalid_file_extension(tmp_path: Path):
    # Create 'order' file and some valid files
    (tmp_path / "order").touch()
    for i in range(1, 500):
        (tmp_path / f"template{i}.gitignore").touch()
    # Add an invalid file
    (tmp_path / "invalid_file.txt").touch()
    with pytest.raises(ValueError, match="is not a valid template file"):
        check_directory_existence_and_validity(tmp_path, ignore_num_files=True)


def test_check_directory_existence_and_validity_insufficient_files(tmp_path: Path):
    (tmp_path / "order").touch()
    for i in range(1, 499):
        (tmp_path / f"template{i}.gitignore").touch()
    with pytest.raises(ValueError, match="should contain at least 500 files"):
        check_directory_existence_and_validity(tmp_path)


def test_check_directory_existence_and_validity_sufficient_files(tmp_path: Path):
    (tmp_path / "order").touch()
    for i in range(1, 501):
        (tmp_path / f"template{i}.gitignore").touch()
    assert check_directory_existence_and_validity(tmp_path) is True


def test_check_directory_existence_and_validity_ignore_num_files(tmp_path: Path):
    (tmp_path / "order").touch()
    for i in range(1, 10):
        (tmp_path / f"template{i}.gitignore").touch()
    assert (
        check_directory_existence_and_validity(tmp_path, ignore_num_files=True) is True
    )


def test_check_directory_existence_and_validity_all_file_types(tmp_path: Path):
    (tmp_path / "order").touch()
    for i in range(1, 200):
        (tmp_path / f"template{i}.gitignore").touch()
        (tmp_path / f"patch{i}.patch").touch()
        (tmp_path / f"stack{i}.stack").touch()
    # Total files: 1(order) + 199*3 = 598 files
    assert check_directory_existence_and_validity(tmp_path) is True


def test_check_directory_existence_and_validity_invalid_files_with_order(
    tmp_path: Path,
):
    (tmp_path / "order").touch()
    # Add some valid files
    for i in range(1, 501):
        (tmp_path / f"template{i}.gitignore").touch()
    # Add some invalid files
    (tmp_path / "readme.md").touch()
    (tmp_path / "script.py").touch()
    with pytest.raises(ValueError, match="is not a valid template file"):
        check_directory_existence_and_validity(tmp_path)


def test_check_directory_existence_and_validity_empty_but_has_order(tmp_path: Path):
    (tmp_path / "order").touch()
    with pytest.raises(ValueError, match="should contain at least 500 files"):
        check_directory_existence_and_validity(tmp_path)
