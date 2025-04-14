import importlib.resources
from pathlib import Path

try:
    # Try to find the package using importlib.resources
    import pygic

    if hasattr(importlib.resources, "files"):  # Python 3.9+
        PACKAGE_DIR = Path(importlib.resources.files(pygic))
    else:  # Python 3.8 or earlier
        PACKAGE_DIR = Path(pygic.__file__).parent

except ImportError:
    PACKAGE_DIR = None


ROOT_DIR = Path(__file__).parents[1]
"""The root directory of the project in absolute path."""

AUTHOR = "Loris FLOQUET"
"""The author of the project, used by `appdirs`."""

VERSION = "0.1.0"
"""The version of the project, used by `appdirs.`"""

TOPTAL_REPO_URL = "https://github.com/toptal/gitignore.git"
"""The URL of the Toptal gitignore repository containing the templates."""
