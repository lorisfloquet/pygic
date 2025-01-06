from click.testing import CliRunner

from pygic.cli import pygic


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(pygic, ["--help"])
    assert result.exit_code == 0
    assert "pygic CLI - A tool for generating gitignores." in result.output
    assert "Commands:" in result.output
