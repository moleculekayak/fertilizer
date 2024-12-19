import os
import re
import shutil
import pytest
import requests_mock

from unittest.mock import MagicMock
from colorama import Fore

from .helpers import SetupTeardown, get_torrent_path, copy_and_mkdir

from fertilizer.errors import TorrentExistsInClientError, TorrentDecodingError
from fertilizer.scanner import scan_torrent_directory, scan_torrent_file


class TestScanTorrentFile(SetupTeardown):
  def test_gets_mad_if_torrent_file_does_not_exist(self, red_api, ops_api):
    with pytest.raises(FileNotFoundError):
      scan_torrent_file("/tmp/nonexistent.torrent", "/tmp/output", red_api, ops_api, None)

  def test_creates_output_directory_if_it_does_not_exist(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.rmtree("/tmp/new_output", ignore_errors=True)

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/new_output", red_api, ops_api, None)

    assert os.path.isdir("/tmp/new_output")
    shutil.rmtree("/tmp/new_output")

  def test_returns_torrent_filepath(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      filepath = scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, None)

      assert os.path.isfile(filepath)
      assert filepath == "/tmp/output/OPS/foo [OPS].torrent"

  def test_calls_injector_if_provided(self, red_api, ops_api):
    injector_mock = MagicMock()
    injector_mock.inject_torrent = MagicMock()
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, injector_mock)

    injector_mock.inject_torrent.assert_called_once_with(
      "/tmp/input/red_source.torrent", "/tmp/output/OPS/foo [OPS].torrent", "OPS"
    )

  def test_calls_injector_if_torrent_is_duplicate(self, red_api, ops_api):
    injector_mock = MagicMock()
    injector_mock.inject_torrent = MagicMock()

    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, injector_mock)

    injector_mock.inject_torrent.assert_called_once_with(
      "/tmp/input/red_source.torrent", "/tmp/output/ops_source.torrent", "OPS"
    )

  def test_doesnt_blow_up_if_other_torrent_name_has_bad_encoding(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("broken_name"), "/tmp/output/broken_name.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, None)

  def test_doesnt_blow_up_if_other_torrent_has_no_info(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("no_info"), "/tmp/input/no_info.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_file("/tmp/input/red_source.torrent", "/tmp/output", red_api, ops_api, None)

  def test_raises_if_torrent_has_no_info(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("no_info"), "/tmp/input/no_info.torrent")

    with pytest.raises(TorrentDecodingError) as excinfo:
      scan_torrent_file("/tmp/input/no_info.torrent", "/tmp/output", red_api, ops_api, None)

    assert "Error decoding torrent file" in str(excinfo.value)


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
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert (
        f"{Fore.LIGHTGREEN_EX}Torrent can be cross-seeded to OPS; successfully generated as '/tmp/output/OPS/foo [OPS].torrent'.{Fore.RESET}"
        in captured.out
      )
      assert f"{Fore.LIGHTGREEN_EX}Generated for cross-seeding{Fore.RESET}: 1" in captured.out

  def test_lists_undecodable_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert f"{Fore.RED}Error decoding torrent file{Fore.RESET}" in captured.out
    assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_tracker_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTBLACK_EX}Torrent not from OPS or RED based on source or announce URL{Fore.RESET}" in captured.out
    )
    assert f"{Fore.LIGHTBLACK_EX}Skipped{Fore.RESET}: 1" in captured.out

  def test_lists_already_existing_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/output/OPS/foo [OPS].torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTYELLOW_EX}Torrent was previously generated.{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_considers_matching_input_torrents_as_already_existing(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/input/ops_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTYELLOW_EX}Torrent already exists in input directory at /tmp/input/red_source.torrent{Fore.RESET}"
      in captured.out
    )

    assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 2" in captured.out

  def test_considers_matching_output_torrents_as_already_existing(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
    captured = capsys.readouterr()

    assert f"{Fore.LIGHTYELLOW_EX}Torrent was previously generated.{Fore.RESET}" in captured.out
    assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_returns_calls_injector_on_duplicate(self, capsys, red_api, ops_api):
    injector_mock = MagicMock()
    injector_mock.inject_torrent = MagicMock()

    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")

    print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, injector_mock))
    captured = capsys.readouterr()

    assert (
      f"{Fore.LIGHTYELLOW_EX}Torrent was previously generated but was injected into your torrent client.{Fore.RESET}"
      in captured.out
    )
    assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out
    injector_mock.inject_torrent.assert_called_once_with(
      "/tmp/input/red_source.torrent", "/tmp/output/ops_source.torrent", "OPS"
    )

  def test_lists_torrents_that_already_exist_in_client(self, capsys, red_api, ops_api):
    injector_mock = MagicMock()
    injector_mock.inject_torrent = MagicMock()
    injector_mock.inject_torrent.side_effect = TorrentExistsInClientError("Torrent exists in client")
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, injector_mock))
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTYELLOW_EX}Torrent exists in client{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTYELLOW_EX}Already exists{Fore.RESET}: 1" in captured.out

  def test_lists_not_found_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.LIGHTRED_EX}Torrent could not be found on OPS{Fore.RESET}" in captured.out
      assert f"{Fore.LIGHTRED_EX}Not found{Fore.RESET}: 1" in captured.out

  def test_lists_unknown_error_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.RED}An unknown error occurred in the API response from OPS{Fore.RESET}" in captured.out
      assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_reports_progress_for_mix_of_torrents(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("ops_announce"), "/tmp/input/ops_announce.torrent")
    copy_and_mkdir(get_torrent_path("no_source"), "/tmp/input/no_source.torrent")
    copy_and_mkdir(get_torrent_path("broken"), "/tmp/input/broken.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert "Analyzed 3 local torrents" in captured.out

      assert (
        f"{Fore.LIGHTGREEN_EX}Torrent can be cross-seeded to RED; successfully generated as '/tmp/output/RED/foo [RED].torrent'.{Fore.RESET}"
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
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/non-torrent.txt")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert "Analyzed 0 local torrents" in captured.out

  def test_calls_injector_if_provided(self, red_api, ops_api):
    injector_mock = MagicMock()
    injector_mock.inject_torrent = MagicMock()
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, injector_mock)

    injector_mock.inject_torrent.assert_called_once_with(
      "/tmp/input/red_source.torrent", "/tmp/output/OPS/foo [OPS].torrent", "OPS"
    )

  def test_doesnt_blow_up_if_other_torrent_name_has_bad_encoding(self, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("broken_name"), "/tmp/input/broken_name.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None)

  def test_doesnt_blow_up_if_input_torrent_has_no_info(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("no_info"), "/tmp/input/no_info.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      print(scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None))
      captured = capsys.readouterr()

      assert f"{Fore.RED}Error decoding torrent file{Fore.RESET}" in captured.out
      assert f"{Fore.RED}Errors{Fore.RESET}: 1" in captured.out

  def test_doesnt_blow_up_if_output_torrent_has_no_info(self, capsys, red_api, ops_api):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    copy_and_mkdir(get_torrent_path("no_info"), "/tmp/output/no_info.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      scan_torrent_directory("/tmp/input", "/tmp/output", red_api, ops_api, None)
