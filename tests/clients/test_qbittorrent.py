import re
import pytest
import requests_mock

from tests.helpers import SetupTeardown, get_torrent_path

from src.errors import TorrentClientError, TorrentClientAuthenticationError, TorrentExistsInClientError
from src.clients.qbittorrent import Qbittorrent


@pytest.fixture
def qbit_client():
  return Qbittorrent("http://admin:supersecret@localhost:8080")


@pytest.fixture
def torrent_info_response():
  return {
    "name": "foo.torrent",
    "state": "Seeding",
    "progress": 1.0,
    "save_path": "/tmp/bar/",
    "content_path": "/tmp/bar/foo",
    "category": "fertilizer",
    "total_remaining": 0.0,
  }


class TestInit(SetupTeardown):
  def test_initializes_with_url_parts(self):
    qbit_client = Qbittorrent("http://admin:supersecret@localhost:8080")

    assert qbit_client._qbit_url_parts == ("http://localhost:8080/api/v2", "admin", "supersecret")

  def test_initializes_with_no_auth(self):
    qbit_client = Qbittorrent("http://localhost:8080")

    assert qbit_client._qbit_url_parts == ("http://localhost:8080/api/v2", "", "")

  def test_initializes_with_no_port(self):
    qbit_client = Qbittorrent("http://admin:supersecret@localhost")

    assert qbit_client._qbit_url_parts == ("http://localhost/api/v2", "admin", "supersecret")


class TestSetup(SetupTeardown):
  def test_sets_auth_cookie(self, qbit_client):
    assert qbit_client._qbit_cookie is None

    with requests_mock.Mocker() as m:
      m.post(re.compile("auth/login"), text="Ok.", headers={"Set-Cookie": "SID=1234;"})

      response = qbit_client.setup()

      assert response
      assert qbit_client._qbit_cookie is not None

  def test_raises_exception_on_failed_auth(self, qbit_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("auth/login"), status_code=403)

      with pytest.raises(TorrentClientAuthenticationError) as excinfo:
        qbit_client.setup()

      assert "qBittorrent login failed" in str(excinfo.value)


class TestGetTorrentInfo(SetupTeardown):
  def test_returns_torrent_details(self, qbit_client, torrent_info_response):
    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), json=[torrent_info_response])

      response = qbit_client.get_torrent_info("1234")

      assert response == {
        "complete": True,
        "label": "fertilizer",
        "save_path": "/tmp/bar/",
        "content_path": "/tmp/bar/foo",
      }

  def test_raises_exception_on_missing_torrent(self, qbit_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), json=[])

      with pytest.raises(TorrentClientError) as excinfo:
        qbit_client.get_torrent_info("1234")

      assert "Torrent not found in client" in str(excinfo.value)

  def test_raises_exception_on_unexpected_response(self, qbit_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), text="")

      with pytest.raises(TorrentClientError) as excinfo:
        qbit_client.get_torrent_info("1234")

      assert "Client returned unexpected response" in str(excinfo.value)

  def test_attempts_reauth_if_cookie_expired(self, qbit_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), status_code=403)
      m.post(re.compile("auth/login"), text="Ok.", headers={"Set-Cookie": "SID=1234;"})

      with pytest.raises(TorrentClientAuthenticationError):
        qbit_client.get_torrent_info("foo")

      assert "torrents/info" in m.request_history[-3].url
      assert "auth/login" in m.request_history[-2].url
      assert "torrents/info" in m.request_history[-1].url


class TestInjectTorrent(SetupTeardown):
  def test_injects_torrent(self, qbit_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), [{"json": [torrent_info_response]}, {"json": []}])
      m.post(re.compile("torrents/add"), json={"hash": "1234"})

      qbit_client.inject_torrent("foo", torrent_path)

      assert "torrents/add" in m.request_history[-1].url
      assert b'name="autoTMM"\r\n\r\nFalse' in m.request_history[-1].body
      assert b'name="category"\r\n\r\nfertilizer' in m.request_history[-1].body
      assert b'name="tags"\r\n\r\nfertilizer' in m.request_history[-1].body
      assert b'name="savepath"\r\n\r\n/tmp/bar/' in m.request_history[-1].body

  def test_uses_save_path_override_if_present(self, qbit_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), [{"json": [torrent_info_response]}, {"json": []}])
      m.post(re.compile("torrents/add"), json={"hash": "1234"})

      qbit_client.inject_torrent("foo", torrent_path, "/tmp/override/")

      assert "torrents/add" in m.request_history[-1].url
      assert b'name="savepath"\r\n\r\n/tmp/override/' in m.request_history[-1].body

  def test_raises_if_source_torrent_isnt_found_in_client(self, qbit_client):
    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), json=[])

      with pytest.raises(TorrentClientError) as excinfo:
        qbit_client.inject_torrent("foo", "bar")

      assert "Torrent not found in client" in str(excinfo.value)

  def test_raises_if_destination_torrent_is_found_in_client(self, qbit_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(re.compile("torrents/info"), [{"json": [torrent_info_response]}, {"json": [torrent_info_response]}])

      with pytest.raises(TorrentExistsInClientError) as excinfo:
        qbit_client.inject_torrent("foo", torrent_path)

      assert "New torrent already exists in client" in str(excinfo.value)
