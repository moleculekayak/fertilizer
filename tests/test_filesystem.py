import os
import pytest

from .helpers import SetupTeardown

from src.filesystem import mkdir_p, assert_path_exists, list_files_of_extension
# from src.errors import ConfigKeyError


class TestMkdirP(SetupTeardown):
  def test_makes_directory(self):
    directory_path = "/tmp/test_mkdir_p/nested"

    mkdir_p(directory_path)

    assert os.path.exists(directory_path)
    os.rmdir(directory_path)

  def test_returns_directory_path(self):
    directory_path = "/tmp/test_mkdir_p"

    assert directory_path == mkdir_p(directory_path)
    os.rmdir(directory_path)


class TestAssertPathExists(SetupTeardown):
  def test_raises_error_on_missing_path(self):
    with pytest.raises(FileNotFoundError) as excinfo:
      assert_path_exists("/tmp/missing")

    assert "File or directory not found: /tmp/missing" in str(excinfo.value)

  def test_returns_path(self):
    path = "/tmp/test_assert_path_exists"

    with open(path, "w") as f:
      f.write("test")

    assert path == assert_path_exists(path)
    os.remove(path)


class TestListFilesOfExtension(SetupTeardown):
  def test_lists_files_of_extension(self):
    input_directory = "tests/support/files"

    files = list_files_of_extension(input_directory)

    assert len(files) > 0
    assert all([file.endswith(".torrent") for file in files])

  def test_allows_specifying_extension(self):
    input_directory = "tests/support"

    files = list_files_of_extension(input_directory, ".json")

    assert len(files) > 0
    assert all([file.endswith(".json") for file in files])

  def test_returns_empty_list_when_no_files_found(self):
    input_directory = "tests/support"

    files = list_files_of_extension(input_directory, ".txt")

    assert len(files) == 0
