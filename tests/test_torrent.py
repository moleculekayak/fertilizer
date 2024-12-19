import os
import re
import pytest
import requests_mock

from .helpers import get_torrent_path, SetupTeardown, copy_and_mkdir

from fertilizer.trackers import RedTracker
from fertilizer.parser import get_bencoded_data
from fertilizer.errors import TorrentAlreadyExistsError, TorrentDecodingError, UnknownTrackerError, TorrentNotFoundError
from fertilizer.torrent import generate_new_torrent_from_file


class TestGenerateNewTorrentFromFile(SetupTeardown):
  def test_saves_new_torrent_from_red_to_ops(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("red_source")
      _, filepath, _ = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_bencoded_data(filepath)

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
      _, filepath, _ = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_bencoded_data(filepath)

      assert parsed_torrent[b"announce"] == b"https://flacsfor.me/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://redacted.sh/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b"RED"

      os.remove(filepath)

  def test_works_with_qbit_fastresume_files(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("qbit_ops")
      _, filepath, _ = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_bencoded_data(filepath)

      assert parsed_torrent[b"announce"] == b"https://flacsfor.me/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://redacted.sh/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b"RED"

      os.remove(filepath)

  def test_returns_expected_tuple(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("ops_source")
      new_tracker, filepath, previously_generated = generate_new_torrent_from_file(
        torrent_path, "/tmp", red_api, ops_api
      )
      get_bencoded_data(filepath)

      assert os.path.isfile(filepath)
      assert new_tracker == RedTracker
      assert previously_generated is False

      os.remove(filepath)

  def test_works_with_alternate_sources_for_creation(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(
        re.compile("action=torrent"),
        [{"json": self.TORRENT_KNOWN_BAD_RESPONSE}, {"json": self.TORRENT_SUCCESS_RESPONSE}],
      )
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("ops_source")
      _, filepath, _ = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_bencoded_data(filepath)

      assert filepath == "/tmp/RED/foo [PTH].torrent"
      assert parsed_torrent[b"announce"] == b"https://flacsfor.me/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://redacted.sh/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b"PTH"

      os.remove(filepath)

  def test_works_with_blank_source_for_creation(self, red_api, ops_api):
    with requests_mock.Mocker() as m:
      m.get(
        re.compile("action=torrent"),
        [
          {"json": self.TORRENT_KNOWN_BAD_RESPONSE},
          {"json": self.TORRENT_KNOWN_BAD_RESPONSE},
          {"json": self.TORRENT_SUCCESS_RESPONSE},
        ],
      )
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      torrent_path = get_torrent_path("ops_source")
      _, filepath, _ = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)
      parsed_torrent = get_bencoded_data(filepath)

      assert filepath == "/tmp/RED/foo.torrent"
      assert parsed_torrent[b"announce"] == b"https://flacsfor.me/bar/announce"
      assert parsed_torrent[b"comment"] == b"https://redacted.sh/torrents.php?torrentid=123"
      assert parsed_torrent[b"info"][b"source"] == b""

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
    input_hashes = {"2AEE440CDC7429B3E4A7E4D20E3839DBB48D72C2": "/path/to/foo"}

    with pytest.raises(TorrentAlreadyExistsError) as excinfo:
      torrent_path = get_torrent_path("red_source")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api, input_hashes)

    assert str(excinfo.value) == "Torrent already exists in input directory at /path/to/foo"

  def test_pre_checks_all_infohashes_for_collision(self, red_api, ops_api):
    # This hash corresponds to that a torrent with the source of "APL"
    input_hashes = {"84508469124335BDE03043105C6E54E00C17B04C": "/path/to/foo"}

    with requests_mock.Mocker() as m:
      with pytest.raises(TorrentAlreadyExistsError) as excinfo:
        torrent_path = get_torrent_path("red_source")
        generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api, input_hashes)

      assert str(excinfo.value) == "Torrent already exists in input directory at /path/to/foo"
      assert m.call_count == 0

  def test_returns_appropriately_if_infohash_found_in_output(self, red_api, ops_api):
    output_hashes = {"2AEE440CDC7429B3E4A7E4D20E3839DBB48D72C2": "bar"}

    torrent_path = get_torrent_path("red_source")
    _, _, previously_generated = generate_new_torrent_from_file(
      torrent_path, "/tmp", red_api, ops_api, {}, output_hashes
    )

    assert previously_generated

  def test_returns_appropriately_if_torrent_already_exists(self, red_api, ops_api):
    torrent_path = get_torrent_path("red_source")
    copy_and_mkdir(torrent_path, "/tmp/OPS/foo [OPS].torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      _, _, previously_generated = generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert previously_generated

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

  def test_raises_error_if_torrent_has_no_info(self, red_api, ops_api):
    with pytest.raises(TorrentDecodingError) as excinfo:
      torrent_path = get_torrent_path("no_info")
      generate_new_torrent_from_file(torrent_path, "/tmp", red_api, ops_api)

    assert str(excinfo.value) == "Error decoding torrent file"
