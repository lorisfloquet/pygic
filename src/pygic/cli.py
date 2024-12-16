from typing import Callable, Optional, Tuple

import click
from click_help_colors import HelpColorsGroup


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def pygic():
    """pygic CLI - A tool for generating gitignores."""


def force_clone_option(func: Callable) -> Callable:
    return click.option(
        "--force-clone",
        is_flag=True,
        help="Enforce cloning of the toptal/gitignore repository, even if already cloned.",
    )(func)


def clone_option(func: Callable) -> Callable:
    def callback(
        ctx: click.Context, param: click.Parameter, value: Optional[str]
    ) -> str:
        if value is None:
            return "default"
        return value

    return click.option(
        "--clone",
        default=None,
        callback=callback,
        help="Directory to clone the toptal/gitignore repository into. The default cloning path will be used if TEXT is not provided.",
    )(func)


def ignore_num_files_check_option(func: Callable) -> Callable:
    return click.option(
        "--ignore-num-files-check",
        is_flag=True,
        help="Disable checking the number of files in the templates directory.",
    )(func)


@pygic.command()
@click.argument("names", nargs=-1, required=True)
@clone_option
@force_clone_option
@ignore_num_files_check_option
def gen(
    names: Tuple[str, ...],
    clone: str,
    force_clone: bool,
    ignore_num_files_check: bool,
):
    """Generate a gitignore file using the template of the given NAMES."""
    click.echo(f"Generating gitignore with force_clone={force_clone}")


@pygic.command(help="Detect tools/languages and generate a .gitignore.")
@clone_option
@force_clone_option
@ignore_num_files_check_option
def autogen(clone: str, force_clone: bool, ignore_num_files_check: bool):
    """Automatically detect the programming languages and tools used in the current project"""
    click.echo(f"Auto-generating resources with force_clone={force_clone}")


@pygic.command(help="Search for templates and generate a .gitignore.")
@click.option(
    "-n",
    "--num-templates",
    default=2,
    help="Number of templates to search for. Default is 2.",
)
@clone_option
@force_clone_option
@ignore_num_files_check_option
def search(
    num_templates: int, clone: str, force_clone: bool, ignore_num_files_check: bool
):
    """Search for NUM_TEMPLATES names among the available gitignore templates
    and generate a gitignore file using the selected templates.
    """
    click.echo(
        f"Searching templates with force_clone={force_clone} and num_templates={num_templates}"
    )


if __name__ == "__main__":
    pygic()
