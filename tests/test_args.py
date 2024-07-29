import pytest

from .support import SetupTeardown

from src.args import parse_args

class TestArgs(SetupTeardown):
  def test_parses_args(self):
    args = parse_args(["-i", "foo", "-o", "bar"])

    assert args.input_directory == "foo"
    assert args.output_directory == "bar"
    assert args.config_file == "src/settings.json"

  def test_requires_input_directory(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-o", "bar"])
    
    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "the following arguments are required: -i/--input-directory" in captured.err

  def test_requires_output_directory(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-i", "foo"])
    
    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "the following arguments are required: -o/--output-directory" in captured.err

  def test_optionally_takes_config_file(self):
    args = parse_args(["-i", "foo", "-o", "bar", "-c", "baz.json"])

    assert args.config_file == "baz.json"
