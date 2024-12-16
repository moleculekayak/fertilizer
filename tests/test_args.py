import pytest

from .helpers import SetupTeardown

from fertilizer.args import parse_args


class TestArgs(SetupTeardown):
  def test_parses_args(self):
    args = parse_args(["-i", "foo", "-o", "bar"])

    assert args.input_directory == "foo"
    assert args.output_directory == "bar"
    assert args.config_file == "src/fertilizer/config.json"

  def test_sets_input_directory(self, capsys):
    args = parse_args(["-i", "foo", "-o", "bar"])

    assert args.input_directory == "foo"

  def test_sets_input_file(self, capsys):
    args = parse_args(["-f", "foo", "-o", "bar"])

    assert args.input_file == "foo"

  def test_requires_an_input_type(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-o", "foo"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "one of the arguments -i/--input-directory -f/--input-file is required" in captured.err

  def test_does_not_allow_both_input_types(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-i", "foo", "-f", "bar", "-o", "baz"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "argument -f/--input-file: not allowed with argument -i/--input-directory" in captured.err

  def test_server_requires_input_directory(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-s", "-o", "foo", "-f", "bar"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    print(captured.err)
    assert "--server requires --input-directory" in captured.err

  def test_requires_output_directory(self, capsys):
    with pytest.raises(SystemExit) as excinfo:
      parse_args(["-i", "foo"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "the following arguments are required: -o/--output-directory" in captured.err

  def test_sets_config_file_location(self):
    args = parse_args(["-i", "foo", "-o", "bar", "-c", "baz.json"])

    assert args.config_file == "baz.json"
