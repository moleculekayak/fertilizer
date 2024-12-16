import pytest
import requests_mock

from .helpers import SetupTeardown

from fertilizer.errors import AuthenticationError
from fertilizer.api import GazelleAPI


class MockApi(GazelleAPI):
  def __init__(self, api_key, delay_in_seconds=2):
    super().__init__(
      site_url="https://foo.bar",
      tracker_url="https://baz.qux",
      auth_header={"Authorization": f"token {api_key}"},
      rate_limit=delay_in_seconds,
    )


@pytest.fixture
def mock_api_instance():
  instance = MockApi("supersecret")
  instance._max_retries = 1
  return instance


class TestGazelleGetAccountInfo(SetupTeardown):
  def test_passes_the_correct_params(self, mock_api_instance):
    with requests_mock.Mocker() as m:
      m.get("https://foo.bar/ajax.php?action=index", json={"status": "success"})
      mock_api_instance.get_account_info()

      assert m.request_history[0].query == "action=index"

  def test_returns_parsed_json_if_successful(self, mock_api_instance):
    with requests_mock.Mocker() as m:
      m.get("https://foo.bar/ajax.php?action=index", json={"status": "success", "result": "you did it!"})
      response = mock_api_instance.get_account_info()

      assert isinstance(response, dict)
      assert response["result"] == "you did it!"

  def test_returns_authentication_error_if_unsuccessful(self, mock_api_instance):
    with pytest.raises(AuthenticationError) as excinfo:
      with requests_mock.Mocker() as m:
        m.get("https://foo.bar/ajax.php?action=index", json={"status": "failure", "error": "you didn't do it!"})
        mock_api_instance.get_account_info()

    assert str(excinfo.value) == "you didn't do it!"


class TestGazelleGetFindTorrent(SetupTeardown):
  def test_passes_the_correct_params(self, mock_api_instance):
    with requests_mock.Mocker() as m:
      m.get("https://foo.bar/ajax.php?hash=321cba&action=torrent", json={})
      mock_api_instance.find_torrent("321cba")

      assert m.request_history[0].query == "hash=321cba&action=torrent"

  def test_returns_parsed_json(self, mock_api_instance):
    with requests_mock.Mocker() as m:
      m.get("https://foo.bar/ajax.php?hash=321cba&action=torrent", json={"info": "success"})
      response = mock_api_instance.find_torrent("321cba")

      assert isinstance(response, dict)
      assert response["info"] == "success"


class TestGazelleAnnounceUrl(SetupTeardown):
  def test_returns_announce_url_if_set(self, mock_api_instance):
    instance = mock_api_instance
    instance._announce_url = "https://baz.qux/123abc/announce"

    assert instance.announce_url == "https://baz.qux/123abc/announce"

  def test_fetches_then_returns_announce_url_if_not_set(self, mock_api_instance):
    with requests_mock.Mocker() as m:
      m.get(
        "https://foo.bar/ajax.php?action=index",
        json={
          "status": "success",
          "response": {
            "passkey": "mypasskey",
          },
        },
      )
      instance = mock_api_instance
      response = instance.announce_url

      assert response == "https://baz.qux/mypasskey/announce"
      assert instance._announce_url == response
