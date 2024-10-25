import re
import pytest
import requests_mock

from tests.helpers import SetupTeardown, get_torrent_path

from src.errors import TorrentClientError, TorrentClientAuthenticationError, TorrentExistsInClientError
from src.clients.transmission import TransmissionBt


@pytest.fixture
def transmission_client():
  return TransmissionBt("http://admin:supersecret@localhost:51314")


@pytest.fixture
def torrent_info_response():
  return {
    "arguments": {
      "torrents": [
        {
          "name": "foo.torrent",
          "percentDone": 1.0,
          "doneDate": 0,
          "status": 6,
          "labels": ["bar"],
          "downloadDir": "/tmp/baz",
        }
      ]
    }
  }


class TestInit(SetupTeardown):
  def test_initializes_with_url_parts(self):
    transmission_client = TransmissionBt("http://admin:supersecret@localhost:51314")

    assert transmission_client._base_url == "http://localhost:51314/transmission/rpc"
    assert transmission_client._basic_auth.username == "admin"
    assert transmission_client._basic_auth.password == "supersecret"


class TestSetup(SetupTeardown):
  def test_sets_session_id(self, transmission_client):
    assert transmission_client._transmission_session_id is None

    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), headers={"X-Transmission-Session-Id": "1234"}, status_code=409)

      transmission_client.setup()

      assert transmission_client._transmission_session_id == "1234"

  def test_raises_exception_on_failed_auth(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), status_code=403)

      with pytest.raises(TorrentClientAuthenticationError):
        transmission_client.setup()

  def test_raises_exception_if_no_session_id(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), status_code=409)

      with pytest.raises(TorrentClientAuthenticationError):
        transmission_client.setup()


class TestGetTorrentInfo(SetupTeardown):
  def test_returns_torrent_info(self, transmission_client, torrent_info_response):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), json=torrent_info_response)

      response = transmission_client.get_torrent_info("infohash")

      assert response == {
        "complete": True,
        "label": ["bar"],
        "save_path": "/tmp/baz",
        "content_path": "/tmp/baz/foo.torrent",
      }

  def test_passes_headers_to_request(self, transmission_client, torrent_info_response):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), headers={"X-Transmission-Session-Id": "1234"}, status_code=409)
      transmission_client.setup()

    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), json=torrent_info_response)

      transmission_client.get_torrent_info("infohash")

      assert m.last_request.headers["X-Transmission-Session-Id"] == transmission_client._transmission_session_id

  def test_passes_json_body_to_request(self, transmission_client, torrent_info_response):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), json=torrent_info_response)

      transmission_client.get_torrent_info("infohash")

      assert m.last_request.json() == {
        "method": "torrent-get",
        "arguments": {
          "ids": ["infohash"],
          "fields": ["labels", "downloadDir", "percentDone", "status", "doneDate", "name"],
        },
      }

  def test_raises_if_json_error(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), text="not json")

      with pytest.raises(TorrentClientError, match="Client returned malformed json response"):
        transmission_client.get_torrent_info("infohash")

  def test_raises_if_no_torrents_found(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), json={"arguments": {"torrents": []}})

      with pytest.raises(TorrentClientError, match="Torrent not found in client"):
        transmission_client.get_torrent_info("infohash")

  def test_raises_on_unexpected_response(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), text="")

      with pytest.raises(TorrentClientError, match="Client returned unexpected response"):
        transmission_client.get_torrent_info("infohash")


class TestInjectTorrent(SetupTeardown):
  def test_injects_torrent(self, transmission_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(
        re.compile("transmission/rpc"), [{"json": torrent_info_response}, {"json": {"arguments": {"torrents": []}}}]
      )

      transmission_client.inject_torrent("foo", torrent_path)

      assert b'"method": "torrent-add"' in m.request_history[-1].body
      assert b'"download-dir": "/tmp/baz"' in m.request_history[-1].body
      assert b'"labels": ["bar"]' in m.request_history[-1].body
      assert b'"metainfo"' in m.request_history[-1].body

  def test_uses_save_path_override_if_present(self, transmission_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(
        re.compile("transmission/rpc"), [{"json": torrent_info_response}, {"json": {"arguments": {"torrents": []}}}]
      )

      transmission_client.inject_torrent("foo", torrent_path, "/tmp/override/")

      assert b'"download-dir": "/tmp/override/"' in m.request_history[-1].body

  def test_raises_if_source_torrent_isnt_found_in_client(self, transmission_client):
    with requests_mock.Mocker() as m:
      m.post(
        re.compile("transmission/rpc"),
        [{"json": {"arguments": {"torrents": []}}}, {"json": {"arguments": {"torrents": []}}}],
      )

      with pytest.raises(TorrentClientError, match="Torrent not found in client"):
        transmission_client.inject_torrent("foo", "bar.torrent")

  def test_raises_if_destination_torrent_is_found_in_client(self, transmission_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(re.compile("transmission/rpc"), [{"json": torrent_info_response}, {"json": torrent_info_response}])

      with pytest.raises(TorrentExistsInClientError, match="New torrent already exists in client"):
        transmission_client.inject_torrent("foo", torrent_path)
