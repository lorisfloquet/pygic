from pathlib import Path

import pytest

from pygic.file import File, FileType
from pygic.templates import TEMPLATES_LOCAL_DIR


class TestFileType:
    """Test suite for the File enum."""

    def test_values(self):
        """Test that FileType.values() returns the correct list of values."""
        expected_values = ["gitignore", "patch", "stack"]
        assert FileType.values() == expected_values


class TestFile:
    """Test suite for the File class."""

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised when the file does not exist."""
        with pytest.raises(FileNotFoundError):
            File(Path("nonexistent_file.gitignore"))

    def test_initialization(self, tmp_path: Path):
        """Test that a File object is correctly initialized when the file exists."""
        test_file = tmp_path / "Test.gitignore"
        test_file.write_text("Some content")

        file_obj = File(test_file)

        assert file_obj.path == test_file
        assert file_obj.type == FileType.GITIGNORE
        assert file_obj.name == "Test"

    @pytest.mark.parametrize(
        "filename,expected_type",
        [
            ("Python.gitignore", FileType.GITIGNORE),
            ("Node.patch", FileType.PATCH),
            ("LAMP.stack", FileType.STACK),
        ],
    )
    def test_type(self, tmp_path: Path, filename: str, expected_type: FileType):
        """Test that File.type is correctly set based on the extension."""
        test_file = tmp_path / filename
        test_file.write_text("Some content")

        file_obj = File(test_file)

        assert file_obj.type == expected_type

    def test_name(self, tmp_path: Path):
        """Test that File.name is correctly set based on the filename."""
        test_file = tmp_path / "Python.gitignore"
        test_file.write_text("Some content")

        file_obj = File(test_file)

        assert file_obj.name == "Python"

    def test_symlink_resolution(self, tmp_path: Path):
        """Test that symlinks are resolved correctly."""
        real_file = tmp_path / "RealFile.gitignore"
        real_file.write_text("Real file content")

        symlink_file = tmp_path / "SymlinkFile.gitignore"
        symlink_file.symlink_to(real_file)

        file_obj = File(symlink_file)

        assert file_obj.path == real_file.resolve()
        assert file_obj.type == FileType.GITIGNORE
        assert file_obj.name == "SymlinkFile"

    def test_get_content(self, tmp_path: Path):
        """Test that get_content() reads the file content correctly."""
        content = "This is a test content."
        test_file = tmp_path / "Test.gitignore"
        test_file.write_text(content)

        file_obj = File(test_file)

        assert file_obj.get_content() == content

    def test_real_file_initialization(self):
        """Test initializing File with a real file from TEMPLATES_LOCAL_DIR."""
        test_file = TEMPLATES_LOCAL_DIR / "Python.gitignore"

        if not test_file.exists():
            pytest.skip("Python.gitignore not found in TEMPLATES_LOCAL_DIR")

        file_obj = File(test_file)

        assert file_obj.path == test_file
        assert file_obj.type == FileType.GITIGNORE
        assert file_obj.name == "Python"

    def test_real_file_get_content(self):
        """Test get_content() with a real file from TEMPLATES_LOCAL_DIR."""
        test_file = TEMPLATES_LOCAL_DIR / "Python.gitignore"

        if not test_file.exists():
            pytest.skip("Python.gitignore not found in TEMPLATES_LOCAL_DIR")

        file_obj = File(test_file)
        content = file_obj.get_content()

        assert isinstance(content, str)
        assert len(content) > 0  # Ensure the content is not empty

    def test_unsupported_file_type(self, tmp_path: Path):
        """Test that initializing File with an unsupported extension raises ValueError."""
        test_file = tmp_path / "Test.unsupported"
        test_file.write_text("Some content")

        with pytest.raises(ValueError):
            File(test_file)
