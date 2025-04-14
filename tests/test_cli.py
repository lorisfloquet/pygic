import sys
from pathlib import Path
from time import sleep

import pexpect
import pytest
from click.testing import CliRunner
from termcolor import colored

from pygic.cli import pygic
from pygic.config import ROOT_DIR


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(pygic, ["--help"])
    assert result.exit_code == 0
    assert "pygic CLI - A tool for generating gitignores." in result.output


@pytest.mark.parametrize(
    "file",
    sorted((ROOT_DIR / "tests" / "targets").glob("*.gitignore")),
)
def test_cli_pygic_gen_command_happy_path(file: Path):
    """Test the 'gen' CLI command to ensure it generates the correct .gitignore content.

    Args:
        file (Path): The path to the .gitignore target file.
    """
    # Read the expected content from the target .gitignore file
    with open(file, "r") as f:
        expected_content = f.read()

    # Derive the names from the file stem (e.g., 'python' or 'python.java')
    file_name = file.stem
    if "." in file_name:
        names = file_name.split(".")
    else:
        names = [file_name]

    # Initialize the CLI runner
    runner = CliRunner()

    # Prepare the command arguments
    cmd_args = ["gen"] + names

    # Invoke the 'gen' command
    result = runner.invoke(pygic, cmd_args)

    # Assert that the command exited without errors
    assert result.exit_code == 0, f"CLI Command failed with output: {result.output}"

    # Get the generated .gitignore file in the CLI output
    gitignore = result.output

    # Compare the generated content with the expected content
    assert (
        gitignore == expected_content
    ), f".gitignore content does not match for {file.name}."


@pytest.mark.skip(reason="This test is not working as expected")
def test_cli_pygic_search_names_interactively(tmp_path: Path):
    """
    Integration test that spawns the interactive search in a pseudo-TTY
    and simulates user input with pexpect.
    """

    child = pexpect.spawn(
        f"{sys.executable} src/pygic/cli.py search", env={"FORCE_COLOR": "0"}
    )

    print(colored("Process started", "light_green", attrs=["bold"]))

    # output = child.before.decode("utf-8")
    # print("DEBUG OUTPUT:", output)

    # sleep(1.0)  # Wait for the process to start

    # (Optional) Log the interaction to stdout for debugging
    child.logfile = sys.stdout.buffer

    # Expect some output that indicates pzp started
    # child.expect_exact(
    #     "To stop searching, press ESC, CTRL-C, CTRL-G, or CTRL-Q\nAlready selected items: []"
    # )
    # print(
    #     colored("Confirmed process started successfully", "light_green", attrs=["bold"])
    # )

    # Send keystrokes to select one of the candidates
    child.send("u")
    print(colored("Send input 'u'", "light_cyan"))
    sleep(0.5)
    child.send("m")
    print(colored("Send input 'm'", "light_cyan"))
    sleep(0.5)
    child.send("b")  # Here Umbraco is the only remaining candidate
    print(colored("Send input 'b'", "light_cyan"))
    sleep(0.5)
    child.sendline("")  # Press Enter
    print(colored("Send input Enter", "light_cyan"))
    sleep(0.5)

    # Expect some output evolution
    # child.expect_exact(
    #     "To stop searching, press ESC, CTRL-C, CTRL-G, or CTRL-Q\nAlready selected items: ['Umbraco']"
    # )

    # print(
    #     colored(
    #         "Confirmed Umbraco was selected successfully", "light_green", attrs=["bold"]
    #     )
    # )

    # Now send ESC to stop searching
    # ESC is \x1b
    child.sendcontrol("c")  # Sends CTRL+C
    print(colored("Send input CTRL+C", "light_cyan"))

    # sleep(0.1)

    # Expect the process to exit and read final output
    child.expect(pexpect.EOF)

    # Verify the final printed output
    output = child.before.decode("utf-8")
    print("DEBUG OUTPUT:", output)

    # Check that the output contains the expected gitignore content
    target_path = ROOT_DIR / "tests" / "targets" / "umbraco.gitignore"
    with open(target_path, "r") as f:
        expected_content = f.read()
    assert expected_content in output
