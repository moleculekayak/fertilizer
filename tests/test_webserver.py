import re
import os
import pytest
import requests_mock

from .helpers import SetupTeardown, get_torrent_path, copy_and_mkdir

from fertilizer import webserver
from fertilizer.parser import calculate_infohash, get_bencoded_data
from fertilizer.webserver import app as webserver_app


@pytest.fixture()
def app(red_api, ops_api):
  webserver_app.config.update(
    {
      "input_dir": "/tmp/input",
      "output_dir": "/tmp/output",
      "red_api": red_api,
      "ops_api": ops_api,
      "injector": None,
    }
  )

  yield webserver_app


@pytest.fixture()
def client(app):
  return app.test_client()


@pytest.fixture()
def infohash():
  return "0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"


class TestWebserverNotFound(SetupTeardown):
  def test_returns_not_found(self, client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json == {"status": "error", "message": "Not found"}


class TestWebserverWebhook(SetupTeardown):
  def test_requires_infohash_parameter(self, client):
    response = client.post("/api/webhook", data={})
    assert response.status_code == 400
    assert response.json == {"status": "error", "message": "Request must include an 'infohash' parameter"}

  def test_rejects_invalid_infohash(self, client):
    responses = [
      client.post("/api/webhook", data={"infohash": "abc"}),
      client.post("/api/webhook", data={"infohash": "mnopqrstuvwx"}),
      client.post("/api/webhook", data={"infohash": 123}),
    ]

    for response in responses:
      assert response.status_code == 400
      assert response.json == {"status": "error", "message": "Invalid infohash"}

  def test_requires_existing_torrent_file(self, client, infohash):
    response = client.post("/api/webhook", data={"infohash": infohash})
    assert response.status_code == 404
    assert response.json == {"status": "error", "message": f"No torrent found at /tmp/input/{infohash}.torrent"}

  def test_generates_new_torrent_file(self, client, infohash):
    copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/{infohash}.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": infohash})
      assert response.status_code == 201
      assert response.json == {"status": "success", "message": "/tmp/output/OPS/foo [OPS].torrent"}
      assert os.path.exists("/tmp/output/OPS/foo [OPS].torrent")

  def test_resolves_name_based_torrent_file_via_fallback(self, client):
    source_path = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/Some Album (2013) [FLAC].torrent")
    real_infohash = calculate_infohash(get_bencoded_data(source_path)).lower()

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": real_infohash})
      assert response.status_code == 201
      assert response.json == {"status": "success", "message": "/tmp/output/OPS/foo [OPS].torrent"}
      assert os.path.exists("/tmp/output/OPS/foo [OPS].torrent")

  def test_returns_404_when_no_torrent_matches_infohash(self, client, infohash):
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/Some Album (2013) [FLAC].torrent")

    response = client.post("/api/webhook", data={"infohash": infohash})
    assert response.status_code == 404
    assert response.json == {"status": "error", "message": f"No torrent found at /tmp/input/{infohash}.torrent"}

  def test_fallback_skips_undecodable_torrent_files(self, client):
    copy_and_mkdir(get_torrent_path("broken"), "/tmp/input/broken.torrent")
    source_path = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/Some Album (2013) [FLAC].torrent")
    real_infohash = calculate_infohash(get_bencoded_data(source_path)).lower()

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": real_infohash})
      assert response.status_code == 201

  def test_fallback_reads_each_file_at_most_once_per_miss(self, client, infohash, monkeypatch):
    for index in range(10):
      copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/Some Album {index} (2013) [FLAC].torrent")

    read_filepaths = self.__record_fallback_reads(monkeypatch)

    for _ in range(5):
      read_filepaths.clear()
      response = client.post("/api/webhook", data={"infohash": infohash})

      assert response.status_code == 404
      # A miss costs one pass over the input directory and nothing beyond it:
      # no file is decoded twice within a request, and no request reads more
      # files than the directory holds.
      assert len(read_filepaths) == len(set(read_filepaths))
      assert len(read_filepaths) <= 10

  def test_does_not_scan_when_the_infohash_named_file_exists(self, client, infohash, monkeypatch):
    copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/{infohash}.torrent")
    for index in range(10):
      copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/Some Album {index} (2013) [FLAC].torrent")

    read_filepaths = self.__record_fallback_reads(monkeypatch)

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": infohash})

      assert response.status_code == 201
      assert read_filepaths == []

  @staticmethod
  def __record_fallback_reads(monkeypatch):
    read_filepaths = []
    original_get_bencoded_data = webserver.get_bencoded_data

    def recording_get_bencoded_data(filepath):
      read_filepaths.append(filepath)
      return original_get_bencoded_data(filepath)

    monkeypatch.setattr(webserver, "get_bencoded_data", recording_get_bencoded_data)

    return read_filepaths

  def test_returns_okay_if_torrent_already_found(self, client, infohash):
    copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/{infohash}.torrent")
    copy_and_mkdir(get_torrent_path("red_source"), "/tmp/output/OPS/foo [OPS].torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": infohash})
      assert response.status_code == 201
      assert response.json == {"status": "success", "message": "/tmp/output/OPS/foo [OPS].torrent"}

  def test_raises_error_if_torrent_not_found(self, client, infohash):
    copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/{infohash}.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": infohash})
      assert response.status_code == 404
      assert response.json == {"status": "error", "message": "Torrent could not be found on OPS"}

  def test_raises_error_if_unknown_error(self, client, infohash):
    copy_and_mkdir(get_torrent_path("red_source"), f"/tmp/input/{infohash}.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"infohash": infohash})
      assert response.status_code == 500
      assert response.json == {"status": "error", "message": "An unknown error occurred in the API response from OPS"}
