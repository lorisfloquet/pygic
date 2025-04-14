from typing import Callable, Tuple

import rich_click as click


def verbose_option(func: Callable) -> Callable:
    return click.option(
        "-v",
        "--verbose",
        count=True,
        help="Enable verbose mode. Use multiple times to increase verbosity.",
    )(func)


@click.group()
@click.version_option()  # Allow the `--version` option to print the version
@click.pass_context  # Pass the click context to the function
@verbose_option
def pygic(ctx: click.Context, verbose: int):
    """pygic CLI - A tool for generating gitignores."""

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
        help="Directory containing local .gitignore files.",
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

    from pygic import Gitignore

    templates = Gitignore(
        directory=directory,
        clone_directory=clone,
        force_clone=force_clone,
        ignore_num_files_check=ignore_num_files_check,
    )

    gitignore = templates.create(*names)

    click.echo(gitignore, nl=False)


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

    from pygic import Gitignore

    templates = Gitignore(
        directory=directory,
        clone_directory=clone,
        force_clone=force_clone,
        ignore_num_files_check=ignore_num_files_check,
    )

    gitignore = templates.search_and_create()

    click.echo(gitignore, nl=False)


if __name__ == "__main__":
    pygic()
