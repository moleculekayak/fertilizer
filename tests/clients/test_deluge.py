import base64
import pytest
import requests_mock

from tests.helpers import SetupTeardown, get_torrent_path
from tests.support.deluge_matchers import (
  add_label_matcher,
  add_torrent_matcher,
  apply_label_matcher,
  auth_matcher,
  connected_matcher,
  get_labels_matcher,
  label_plugin_matcher,
  torrent_info_matcher,
)

from src.errors import TorrentClientError
from src.clients.deluge import Deluge


@pytest.fixture
def api_url():
  return "http://localhost:8112/json"


@pytest.fixture
def deluge_client():
  return Deluge("http://:supersecret@localhost:8112/json")


@pytest.fixture
def torrent_info_response():
  return {
    "name": "foo.torrent",
    "state": "Seeding",
    "progress": 100.0,
    "save_path": "/tmp/bar/",
    "label": "fertilizer",
    "total_remaining": 0.0,
  }


class TestSetup(SetupTeardown):
  def test_sets_auth_cookie(self, api_url, deluge_client):
    assert deluge_client._deluge_cookie is None

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=auth_matcher,
        json={"result": True},
        headers={"Set-Cookie": "supersecret"},
      )
      m.post(api_url, additional_matcher=connected_matcher, json={"result": True})
      m.post(api_url, additional_matcher=label_plugin_matcher, json={"result": ["Label"]})

      response = deluge_client.setup()

      assert response
      assert deluge_client._deluge_cookie is not None

  def test_raises_exception_on_failed_auth(self, api_url, deluge_client):
    with requests_mock.Mocker() as m:
      m.post(api_url, additional_matcher=auth_matcher, json={"result": False})

      with pytest.raises(TorrentClientError) as excinfo:
        deluge_client.setup()

      assert "Reached Deluge RPC endpoint but failed to authenticate" in str(excinfo.value)

  def test_sets_label_plugin_enabled_when_true(self, api_url, deluge_client):
    assert not deluge_client._label_plugin_enabled

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=auth_matcher,
        json={"result": True},
        headers={"Set-Cookie": "supersecret"},
      )
      m.post(api_url, additional_matcher=connected_matcher, json={"result": True})
      m.post(api_url, additional_matcher=label_plugin_matcher, json={"result": ["Label"]})

      deluge_client.setup()

      assert deluge_client._label_plugin_enabled

  def test_sets_label_plugin_enabled_when_false(self, api_url, deluge_client):
    assert not deluge_client._label_plugin_enabled

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=auth_matcher,
        json={"result": True},
        headers={"Set-Cookie": "supersecret"},
      )
      m.post(api_url, additional_matcher=connected_matcher, json={"result": True})
      m.post(api_url, additional_matcher=label_plugin_matcher, json={"result": []})

      deluge_client.setup()

      assert not deluge_client._label_plugin_enabled


class TestGetTorrentInfo(SetupTeardown):
  def test_returns_torrent_details(self, api_url, deluge_client, torrent_info_response):
    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      response = deluge_client.get_torrent_info("foo")

      assert response == {
        "complete": True,
        "label": "fertilizer",
        "save_path": "/tmp/bar/",
      }

  def test_raises_if_no_torrents_returned(self, api_url, deluge_client):
    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={"result": {}},
      )

      with pytest.raises(TorrentClientError) as excinfo:
        deluge_client.get_torrent_info("foo")

      assert "Client returned unexpected response (object missing)" in str(excinfo.value)

  def test_raises_if_torrent_not_found(self, api_url, deluge_client):
    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={"result": {"torrents": {}}},
      )

      with pytest.raises(TorrentClientError) as excinfo:
        deluge_client.get_torrent_info("foo")

      assert "Torrent not found in client (foo)" in str(excinfo.value)

  def test_returns_completed_if_paused_and_finished(self, api_url, deluge_client, torrent_info_response):
    torrent_info_response["state"] = "Paused"
    torrent_info_response["progress"] = 100.0
    torrent_info_response["total_remaining"] = 0

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      response = deluge_client.get_torrent_info("foo")

      assert response["complete"]

  def test_returns_completed_if_seeding(self, api_url, deluge_client, torrent_info_response):
    torrent_info_response["state"] = "Seeding"

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      response = deluge_client.get_torrent_info("foo")

      assert response["complete"]


class TestInjectTorrent(SetupTeardown):
  def test_injects_torrent(self, api_url, deluge_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      m.post(
        api_url,
        additional_matcher=add_torrent_matcher,
        json={"result": "abc123"},
      )

      response = deluge_client.inject_torrent("foo", torrent_path)
      request_params = m.request_history[1].json()["params"]

      assert response == "abc123"
      assert request_params[0] == "red_source.fertilizer.torrent"
      assert request_params[1] == base64.b64encode(open(torrent_path, "rb").read()).decode()
      assert request_params[2] == {"download_location": "/tmp/bar/", "seed_mode": True, "add_paused": False}

  def test_uses_save_path_override_if_present(self, api_url, deluge_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      m.post(
        api_url,
        additional_matcher=add_torrent_matcher,
        json={"result": "abc123"},
      )

      deluge_client.inject_torrent("foo", torrent_path, "/tmp/override/")
      request_params = m.request_history[1].json()["params"]

      assert request_params[2] == {"download_location": "/tmp/override/", "seed_mode": True, "add_paused": False}

  def test_raises_if_torrent_not_complete(self, api_url, deluge_client, torrent_info_response):
    torrent_info_response["state"] = "Paused"
    torrent_info_response["progress"] = 50.0
    torrent_info_response["total_remaining"] = 50.0

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      with pytest.raises(TorrentClientError) as excinfo:
        deluge_client.inject_torrent("foo", get_torrent_path("red_source"))

      assert "Cannot inject a torrent that is not complete" in str(excinfo.value)

  def test_sets_label(self, api_url, deluge_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")
    deluge_client._label_plugin_enabled = True

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      m.post(api_url, additional_matcher=add_torrent_matcher, json={"result": "abc123"})
      m.post(api_url, additional_matcher=get_labels_matcher, json={"result": ["fertilizer"]})
      m.post(api_url, additional_matcher=apply_label_matcher, json={"result": True})

      deluge_client.inject_torrent("foo", torrent_path)

      assert m.request_history[-1].json()["params"] == ["abc123", "fertilizer"]
      assert m.request_history[-1].json()["method"] == "label.set_torrent"

  def test_adds_label_if_doesnt_exist(self, api_url, deluge_client, torrent_info_response):
    torrent_path = get_torrent_path("red_source")
    deluge_client._label_plugin_enabled = True

    with requests_mock.Mocker() as m:
      m.post(
        api_url,
        additional_matcher=torrent_info_matcher,
        json={
          "result": {
            "torrents": {"foo": torrent_info_response},
          },
        },
      )

      m.post(api_url, additional_matcher=add_torrent_matcher, json={"result": "abc123"})
      m.post(api_url, additional_matcher=get_labels_matcher, json={"result": []})
      m.post(api_url, additional_matcher=add_label_matcher, json={"result": []})
      m.post(api_url, additional_matcher=apply_label_matcher, json={"result": True})

      deluge_client.inject_torrent("foo", torrent_path)

      assert m.request_history[-2].json()["params"] == ["fertilizer"]
      assert m.request_history[-2].json()["method"] == "label.add"
