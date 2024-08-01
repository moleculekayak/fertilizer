import os
import re
import shutil
import pytest
import requests_mock
from colorama import Fore

from .support import SetupTeardown, get_torrent_path

from src.errors import TorrentAlreadyExistsError
from src.scanner import scan_torrent_directory, scan_torrent_file


class TestScanTorrentFile(SetupTeardown):
  def test_gets_mad_if_torrent_file_does_not_exist(self, red_api, ops_api):
    with pytest.raises(FileNotFoundError):
      scan_torrent_file("/tmp/nonexistent.torrent", "/tmp/output", red_api, ops_api, None)

  def test_creates_output_directory_if_it_does_not_exist(self, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.rmtree("/tmp/new_output", ignore_errors=True)

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/new_output", red_api, ops_api, None)

    assert os.path.isdir("/tmp/new_output")
    shutil.rmtree("/tmp/new_output")

  def test_returns_torrent_filepath(self, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      filepath = scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, None)

      assert os.path.isfile(filepath)
      assert filepath == "/tmp/output/foo [OPS].torrent"

  def test_considers_matching_output_torrents_as_already_existing(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, None)

    assert str(excinfo.value) == "Torrent already exists in output directory as Big Buck Bunny"


class TestScanTorrentDirectory(SetupTeardown):
  def test_gets_mad_if_input_directory_does_not_exist(self, red_api, ops_api):
    with pytest.raises(FileNotFoundError):
      scan_torrent_directory("/tmp/nonexistent", "/tmp/output", red_api, ops_api, None)

  def test_creates_output_directory_if_it_does_not_exist(self, red_api, ops_api):
    shutil.rmtree("/tmp/new_output", ignore_errors=True)
    scan_torrent_directory("/tmp/input", "/tmp/new_output", red_api, ops_api, None)

    assert os.path.isdir("/tmp/new_output")
    shutil.rmtree("/tmp/new_output")

  def test_lists_generated_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert (
        f"{Fore.LIGHTGREEN_EX}Found with source 'OPS' and generated as '/tmp/output/foo [OPS].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert f"{Fore.LIGHTGREEN_EX}Generated for cross-seeding{Fore.RESET}: 1" in captured.out

  def test_lists_undecodable_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert f"{Fore.RED}Error decoding torrent file{Fore.RESET}" in captured.out
    assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_tracker_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
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

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert (
        f"{Fore.LIGHTYELLOW_EX}Torrent file already exists at /tmp/output/foo [OPS].torrent{Fore.RESET}" in captured.out
      )
      assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_considers_matching_input_torrents_as_already_existing(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("ops_source"), "/tmp/input/ops_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTYELLOW_EX}Torrent already exists in input directory as Big Buck Bunny{Fore.RESET}" in captured.out
    )
    assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 2" in captured.out

  def test_considers_matching_output_torrents_as_already_existing(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTYELLOW_EX}Torrent already exists in output directory as Big Buck Bunny{Fore.RESET}" in captured.out
    )
    assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_lists_not_found_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTRED_EX}Torrent could not be found on OPS{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTRED_EX}Not found{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_error_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.RED}An unknown error occurred in the API response from OPS{Fore.RESET}" in captured.out
      assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_reports_progress_for_mix_of_torrents(self, capsys, red_api, ops_api):
    shutil.copy(get_torrent_path("ops_announce"), "/tmp/input/ops_announce.torrent")
    shutil.copy(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")
    shutil.copy(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert "Analyzed 3 local torrents" in captured.out

      assert (
        f"{Fore.LIGHTGREEN_EX}Found with source 'RED' and generated as '/tmp/output/foo [RED].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert f"{Fore.LIGHTGREEN_EX}Generated for cross-seeding{Fore.RESET}: 1" in captured.out

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

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert "Analyzed 0 local torrents" in captured.out
