from typing import Callable, Tuple

import click
from click_help_colors import HelpColorsGroup


def verbose_option(func: Callable) -> Callable:
    return click.option(
        "-v",
        "--verbose",
        count=True,
        help="Enable verbose mode. Use multiple times to increase verbosity.",
    )(func)


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
@click.version_option()
@click.pass_context  # Pass the click context to the function
@verbose_option
def pygic(ctx: click.Context, verbose: int):
    """pygic CLI - A tool for generating gitignores."""

    # If no subcommand is provided, print the help message and exit.
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()

    import logging

    from pygic.utils import setup_logging

    # Set up logging based on the provided verbosity level
    # Default to WARNING level
    if verbose == 1:
        setup_logging(logging.INFO)
    elif verbose >= 2:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.WARNING)


def clone_option(func: Callable) -> Callable:
    return click.option(
        "--clone",
        is_flag=False,
        flag_value="default",
        default=None,
        help="If provided, clone the repository. If no TEXT is provided, use the default directory.",
    )(func)


def force_clone_option(func: Callable) -> Callable:
    return click.option(
        "--force-clone",
        is_flag=True,
        help="Enforce cloning of the toptal/gitignore repository, even if already cloned.",
    )(func)


def directory_option(func: Callable) -> Callable:
    return click.option(
        "--directory",
        default=None,
        help="Directory to generate the .gitignore file in.",
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
@directory_option
@ignore_num_files_check_option
def gen(
    names: Tuple[str, ...],
    clone: str,
    force_clone: bool,
    directory: str,
    ignore_num_files_check: bool,
):
    """Generate a gitignore file using the template of the given NAMES."""

    from pygic import Templates

    templates = Templates(
        directory=directory,
        clone_directory=clone,
        force_clone=force_clone,
        ignore_num_files_check=ignore_num_files_check,
    )

    templates.create_gitignore(names)


@pygic.command(help="Detect tools/languages and generate a .gitignore.")
@clone_option
@force_clone_option
@directory_option
@ignore_num_files_check_option
def autogen(
    clone: str, force_clone: bool, directory: str, ignore_num_files_check: bool
):
    """Automatically detect the programming languages and tools used in the current project"""
    click.echo("The autogen command is not yet implemented.")


@pygic.command(help="Search for templates and generate a .gitignore.")
@clone_option
@force_clone_option
@directory_option
@ignore_num_files_check_option
def search(
    clone: str,
    force_clone: bool,
    directory: str,
    ignore_num_files_check: bool,
):
    """
    Search for names among the available gitignore templates
    and generate a gitignore file using the selected templates.
    """

    from pygic import Templates

    templates = Templates(
        directory=directory,
        clone_directory=clone,
        force_clone=force_clone,
        ignore_num_files_check=ignore_num_files_check,
    )

    gitignore = templates.search_and_create()

    click.echo(gitignore)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    pygic()
