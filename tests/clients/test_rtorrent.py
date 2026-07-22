import xmlrpc.client

import pytest
import requests_mock

from tests.helpers import SetupTeardown, get_torrent_path

from fertilizer.parser import get_bencoded_data, calculate_infohash
from fertilizer.filesystem import sane_join
from fertilizer.errors import TorrentClientError, TorrentExistsInClientError
from fertilizer.clients.rtorrent import RTorrent

API_URL = "http://:secret@localhost:8080/RPC2"
HREF = "http://localhost:8080/RPC2"


def xmlrpc_response(value):
  return xmlrpc.client.dumps((value,), methodresponse=True).encode("utf-8")


def xmlrpc_fault(code, message):
  return xmlrpc.client.dumps(xmlrpc.client.Fault(code, message)).encode("utf-8")


def method_matcher(name):
  return lambda request: f"<methodName>{name}</methodName>" in (request.text or "")


def method_hash_matcher(name, infohash):
  return lambda request: (
    f"<methodName>{name}</methodName>" in (request.text or "") and infohash in (request.text or "")
  )


def _mock_torrent_info(
  m, infohash, *, complete=1, directory="/tmp/data", base_path="/tmp/data/foo", name="foo", label="fertilizer"
):
  m.post(HREF, additional_matcher=method_hash_matcher("d.complete", infohash), content=xmlrpc_response(complete))
  m.post(HREF, additional_matcher=method_hash_matcher("d.directory", infohash), content=xmlrpc_response(directory))
  m.post(HREF, additional_matcher=method_hash_matcher("d.base_path", infohash), content=xmlrpc_response(base_path))
  m.post(HREF, additional_matcher=method_hash_matcher("d.name", infohash), content=xmlrpc_response(name))
  m.post(HREF, additional_matcher=method_hash_matcher("d.custom1", infohash), content=xmlrpc_response(label))


@pytest.fixture
def rtorrent_client():
  return RTorrent(API_URL)


class TestSetup(SetupTeardown):
  def test_returns_version(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      m.post(HREF, additional_matcher=method_matcher("system.client_version"), content=xmlrpc_response("0.9.8"))
      assert rtorrent_client.setup() == "0.9.8"

  def test_raises_on_http_error(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      m.post(HREF, additional_matcher=method_matcher("system.client_version"), status_code=500)
      with pytest.raises(TorrentClientError):
        rtorrent_client.setup()


class TestGetTorrentInfo(SetupTeardown):
  def test_returns_torrent_details(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      _mock_torrent_info(m, "ABC")
      info = rtorrent_client.get_torrent_info("abc")

      assert info["complete"] is True
      assert info["label"] == "fertilizer"
      assert info["save_path"] == "/tmp/data"
      assert info["content_path"] == "/tmp/data/foo"

  def test_uppercases_infohash(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      _mock_torrent_info(m, "ABCDEF")
      rtorrent_client.get_torrent_info("abcdef")

      assert "ABCDEF" in m.request_history[0].text

  def test_falls_back_to_joined_path_when_base_path_empty(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      _mock_torrent_info(m, "ABC", base_path="")
      info = rtorrent_client.get_torrent_info("abc")

      assert info["content_path"] == sane_join("/tmp/data", "foo")

  def test_raises_if_torrent_not_found(self, rtorrent_client):
    with requests_mock.Mocker() as m:
      m.post(
        HREF,
        additional_matcher=method_matcher("d.complete"),
        content=xmlrpc_fault(-501, "Could not find info-hash."),
      )
      with pytest.raises(TorrentClientError) as excinfo:
        rtorrent_client.get_torrent_info("abc")

      assert "Torrent not found" in str(excinfo.value)


class TestInjectTorrent(SetupTeardown):
  def _new_hash(self, torrent_path):
    return calculate_infohash(get_bencoded_data(torrent_path)).upper()

  def test_injects_torrent(self, rtorrent_client):
    torrent_path = get_torrent_path("red_source")
    new_hash = self._new_hash(torrent_path)

    with requests_mock.Mocker() as m:
      # the new torrent does not exist yet -> its d.complete lookup faults
      m.post(
        HREF, additional_matcher=method_hash_matcher("d.complete", new_hash), content=xmlrpc_fault(-501, "not found")
      )
      # the source torrent is present and complete
      _mock_torrent_info(m, "SOURCE")
      m.post(HREF, additional_matcher=method_matcher("load.raw_start"), content=xmlrpc_response(0))

      response = rtorrent_client.inject_torrent("source", torrent_path)

      assert response == new_hash.lower()
      load_body = m.request_history[-1].text
      assert "load.raw_start" in load_body
      assert "d.directory.set=/tmp/data" in load_body
      assert "d.custom1.set=fertilizer" in load_body

  def test_uses_save_path_override_if_present(self, rtorrent_client):
    torrent_path = get_torrent_path("red_source")
    new_hash = self._new_hash(torrent_path)

    with requests_mock.Mocker() as m:
      m.post(
        HREF, additional_matcher=method_hash_matcher("d.complete", new_hash), content=xmlrpc_fault(-501, "not found")
      )
      _mock_torrent_info(m, "SOURCE")
      m.post(HREF, additional_matcher=method_matcher("load.raw_start"), content=xmlrpc_response(0))

      rtorrent_client.inject_torrent("source", torrent_path, save_path_override="/tmp/override")

      assert "d.directory.set=/tmp/override" in m.request_history[-1].text

  def test_raises_if_torrent_exists_in_client(self, rtorrent_client):
    torrent_path = get_torrent_path("red_source")
    new_hash = self._new_hash(torrent_path)

    with requests_mock.Mocker() as m:
      # the new torrent already exists -> its lookup succeeds
      _mock_torrent_info(m, new_hash)

      with pytest.raises(TorrentExistsInClientError):
        rtorrent_client.inject_torrent("source", torrent_path)

  def test_raises_if_source_torrent_not_complete(self, rtorrent_client):
    torrent_path = get_torrent_path("red_source")
    new_hash = self._new_hash(torrent_path)

    with requests_mock.Mocker() as m:
      m.post(
        HREF, additional_matcher=method_hash_matcher("d.complete", new_hash), content=xmlrpc_fault(-501, "not found")
      )
      _mock_torrent_info(m, "SOURCE", complete=0)

      with pytest.raises(TorrentClientError) as excinfo:
        rtorrent_client.inject_torrent("source", torrent_path)

      assert "not complete" in str(excinfo.value)
