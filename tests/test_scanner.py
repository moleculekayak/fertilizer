import os
import re
import shutil
import pytest
import requests_mock
from colorama import Fore

from .support import SetupTeardown, get_torrent_path

from src.scanner import scan_torrent_directory


class TestScanTorrentDirectory(SetupTeardown):
  TORRENT_SUCCESS_RESPONSE = {"status": "success", "response": {"torrent": {"filePath": "foo", "id": 123}}}
  TORRENT_KNOWN_BAD_RESPONSE = {"status": "failure", "error": "bad hash parameter"}
  TORRENT_UNKNOWN_BAD_RESPONSE = {"status": "failure", "error": "unknown error"}
  ANNOUNCE_SUCCESS_RESPONSE = {"status": "success", "response": {"passkey": "bar"}}

  def setup_method(self):
    super().setup_method()
    shutil.rmtree("/tmp/input", ignore_errors=True)
    shutil.rmtree("/tmp/output", ignore_errors=True)
    os.makedirs("/tmp/input")
    os.makedirs("/tmp/output")

  def test_gets_mad_if_input_directory_does_not_exist(self, red_api, ops_api):
    with pytest.raises(FileNotFoundError):
      scan_torrent_directory("/tmp/nonexistent", "/tmp/output", red_api, ops_api)

  def test_creates_output_directory_if_it_does_not_exist(self, capsys, red_api, ops_api):
    scan_torrent_directory("/tmp/input", "/tmp/new_output", red_api, ops_api)
    # suppress stdout/stderr
    capsys.readouterr()
    assert os.path.isdir("/tmp/new_output")

    os.rmdir("/tmp/new_output")

  def test_lists_generated_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert (
        f"{Fore.LIGHTGREEN_EX}Found with source 'OPS' and generated as '/tmp/output/foo [OPS].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert f"{Fore.LIGHTGREEN_EX}Generated for cross-seeding{Fore.RESET}: 1" in captured.out

  def test_lists_undecodable_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
    captured = capsys.readouterr()

    assert f"{Fore.RED}Error decoding torrent file{Fore.RESET}" in captured.out
    assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_tracker_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")

    scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTBLACK_EX}Torrent not from OPS or RED based on source or announce URL{Fore.RESET}" in captured.out
    )
    assert f"{Fore.LIGHTBLACK_EX}Skipped{Fore.RESET}: 1" in captured.out

  def test_lists_already_existing_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("red_source"), "/tmp/output/foo [OPS].torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTYELLOW_EX}Found, but the output .torrent already exists.{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_lists_not_found_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTRED_EX}Torrent could not be found on OPS{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTRED_EX}Not found{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_error_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert f"{Fore.RED}An unknown error occurred in the API response from OPS{Fore.RESET}" in captured.out
      assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_reports_progress_for_mix_of_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("ops_source"), "/tmp/input/ops_source.torrent")
    shutil.copy(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")
    shutil.copy(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert "Analyzed 4 local torrents" in captured.out

      assert (
        f"{Fore.LIGHTGREEN_EX}Found with source 'OPS' and generated as '/tmp/output/foo [OPS].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert (
        f"{Fore.LIGHTGREEN_EX}Found with source 'RED' and generated as '/tmp/output/foo [RED].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert f"{Fore.LIGHTGREEN_EX}Generated for cross-seeding{Fore.RESET}: 2" in captured.out

      assert (
        f"{Fore.LIGHTBLACK_EX}Torrent not from OPS or RED based on source or announce URL{Fore.RESET}" in captured.out
      )
      assert f"{Fore.LIGHTBLACK_EX}Skipped{Fore.RESET}: 1" in captured.out

      assert f"{Fore.RED}Error decoding torrent file{Fore.RESET}" in captured.out
      assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_doesnt_care_about_other_files_in_input_directory(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/non-torrent.txt")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api)
      captured = capsys.readouterr()

      assert "Analyzed 0 local torrents" in captured.out
