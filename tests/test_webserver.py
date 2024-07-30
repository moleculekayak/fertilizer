import re
import os
import pytest
import shutil
import requests_mock

from .support import SetupTeardown, get_torrent_path

from src.webserver import app as webserver_app


@pytest.fixture()
def app(red_api, ops_api):
  webserver_app.config.update(
    {
      "output_dir": "/tmp/output",
      "red_api": red_api,
      "ops_api": ops_api,
    }
  )

  yield webserver_app


@pytest.fixture()
def client(app):
  return app.test_client()


class TestWebserverWebhook(SetupTeardown):
  def test_requires_path_parameter(self, client):
    response = client.post("/api/webhook", data={})
    assert response.status_code == 400
    assert response.json == {"status": "error", "message": "Request must include a 'path' parameter"}

  def test_requires_path_to_torrent_file(self, client):
    response = client.post("/api/webhook", data={"path": "foo"})
    assert response.status_code == 400
    assert response.json == {"status": "error", "message": "'path' must point to a .torrent file"}

  def test_requires_existing_torrent_file(self, client):
    response = client.post("/api/webhook", data={"path": "foo.torrent"})
    assert response.status_code == 404
    assert response.json == {"status": "error", "message": "No torrent found at foo.torrent"}

  def test_generates_new_torrent_file(self, client):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"path": "/tmp/input/red_source.torrent"})
      assert response.status_code == 201
      assert response.json == {"status": "success", "message": "/tmp/output/foo [OPS].torrent"}
      assert os.path.exists("/tmp/output/foo [OPS].torrent")

  def test_returns_error_if_torrent_already_exists(self, client):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    shutil.copy(get_torrent_path("red_source"), "/tmp/output/foo [OPS].torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_SUCCESS_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"path": "/tmp/input/red_source.torrent"})
      assert response.status_code == 409
      assert response.json == {
        "status": "error",
        "message": "Torrent file already exists at /tmp/output/foo [OPS].torrent",
      }

  def test_returns_error_if_torrent_not_found(self, client):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_KNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"path": "/tmp/input/red_source.torrent"})
      assert response.status_code == 404
      assert response.json == {"status": "error", "message": "Torrent could not be found on OPS"}

  def test_returns_error_if_unknown_error(self, client):
    shutil.copy(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")

    with requests_mock.Mocker() as m:
      m.get(re.compile("action=torrent"), json=self.TORRENT_UNKNOWN_BAD_RESPONSE)
      m.get(re.compile("action=index"), json=self.ANNOUNCE_SUCCESS_RESPONSE)

      response = client.post("/api/webhook", data={"path": "/tmp/input/red_source.torrent"})
      assert response.status_code == 500
      assert response.json == {"status": "error", "message": "An unknown error occurred in the API response from OPS"}
