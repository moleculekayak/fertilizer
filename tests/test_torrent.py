import os
import re
import pytest
import requests_mock

from .support import get_torrent_path, SetupTeardown

from src.trackers import RedTracker
from src.parser import get_torrent_data
from src.errors import TorrentAlreadyExistsError, TorrentDecodingError, UnknownTrackerError, TorrentNotFoundError
from src.torrent import generate_new_torrent_from_file, generate_torrent_output_filepath


class TestGenerateNewTorrentFromFile(SetupTeardown):
  def test_saves_new_torrent_from_red_to_ops(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("red_source")
      _, filepath = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_torrent_data(filepath)

      assert os.path.isfile(filepath)
      assert parsed_torrent[b"announce"] == b"https://home.opsfet.ch/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://orpheus.network/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b"OPS"

      os.remove(filepath)

  def test_saves_new_torrent_from_ops_to_red(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("ops_source")
      _, filepath = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_torrent_data(filepath)

      assert parsed_torrent[b"announce"] == b"https://flacsfor.me/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://redacted.ch/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b"RED"

      os.remove(filepath)

  def test_returns_new_tracker_instance_and_filepath(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("ops_source")
      new_tracker, filepath = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      get_torrent_data(filepath)

      assert os.path.isfile(filepath)
      assert new_tracker == RedTracker

      os.remove(filepath)

  def test_raises_error_if_cannot_decode_torrent(self, red_api, ops_api):
    with pytest.raises(TorrentDecodingError) as excinfo:
      torrent_path = get_torrent_path("broken")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == "Error decoding torrent file"

  def test_raises_error_if_tracker_not_found(self, red_api, ops_api):
    with pytest.raises(UnknownTrackerError) as excinfo:
      torrent_path = get_torrent_path("no_source")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == "Torrent not from OPS or RED based on source or announce URL"

  def test_raises_error_if_infohash_found_in_input(self, red_api, ops_api):
    input_hashes = {"2AEE440CDC7429B3E4A7E4D20E3839DBB48D72C2": "foo"}

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      torrent_path = get_torrent_path("red_source")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api, input_hashes)

    assert str(excinfo.value) == "Torrent already exists in input directory as foo"

  def test_raises_error_if_infohash_found_in_output(self, red_api, ops_api):
    output_hashes = {"2AEE440CDC7429B3E4A7E4D20E3839DBB48D72C2": "bar"}

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      torrent_path = get_torrent_path("red_source")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api, {}, output_hashes)

    assert str(excinfo.value) == "Torrent already exists in output directory as bar"

  def test_raises_error_if_torrent_already_exists(self, red_api, ops_api):
    filepath = generate_torrent_output_filepath(self.TORRENT_SUCCESS_RESPONSE, "OPS", "/tmp")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
      f.write("")

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      with requests_mock.Mocker() as m:
        m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
        m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

        torrent_path = get_torrent_path("red_source")
        generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == f"Torrent file already exists at {filepath}"
    os.remove(filepath)

  def test_raises_error_if_api_response_error(self, red_api, ops_api):
    with pytest.raises(TorrentNotFoundError) as excinfo:
      with requests_mock.Mocker() as m:
        m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
        m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

        torrent_path = get_torrent_path("red_source")
        generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == "Torrent could not be found on OPS"

  def test_raises_error_if_api_response_unknown(self, red_api, ops_api):
    with pytest.raises(Exception) as excinfo:
      with requests_mock.Mocker() as m:
        m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
        m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

        torrent_path = get_torrent_path("red_source")
        generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == "An unknown error occurred in the API response from OPS"


class TestGenerateTorrentOutputFilepath(SetupTeardown):
  API_RESPONSE = {"response": {"torrent": {"filePath": "foo"}}}

  def test_constructs_a_path_from_response_and_source(self):
    filepath = generate_torrent_output_filepath(self.API_RESPONSE, "OPS", "base/dir")

    assert filepath == "base/dir/OPS/foo [OPS].torrent"

  def test_raises_error_if_file_exists(self):
    filepath = generate_torrent_output_filepath(self.API_RESPONSE, "OPS", "/tmp")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
      f.write("")

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      generate_torrent_output_filepath(self.API_RESPONSE, "OPS", "/tmp")

    assert str(excinfo.value) == f"Torrent file already exists at {filepath}"
    os.remove(filepath)
