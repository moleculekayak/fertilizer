import json
import requests

from ..errors import TorrentClientError
from .torrent_client import TorrentClient
from requests.exceptions import RequestException
from requests.structures import CaseInsensitiveDict


class Deluge(TorrentClient):
  def __init__(self, rpc_url):
    self._rpc_url = rpc_url
    self._deluge_cookie = None
    self._deluge_request_id = 0
    self._label_plugin_enabled = False

  def setup(self):
    connection_response = self.authenticate()
    self._label_plugin_enabled = self.__is_label_plugin_enabled()

    return connection_response

  def authenticate(self):
    _href, _username, password = self._extract_credentials_from_url(self._rpc_url)
    if not password:
      raise Exception("You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112)")

    auth_response = self.__request("auth.login", [password])
    if not auth_response:
      raise TorrentClientError("Reached Deluge RPC endpoint but failed to authenticate")

    return self.__request("web.connected")
  
  def get_torrent_info(self, infohash):
    params = [
      [
        "name",
        "state",
        "progress",
        "save_path",
        "label",
        "total_remaining",
      ],
      {"hash": infohash},
    ]

    response = self.__request("web.update_ui", params)
    if 'torrents' in response:
      torrent = response['torrents'].get(infohash)

      if torrent is None:
        raise ValueError(f"Torrent not found in client ({infohash})")
    else:
      raise TorrentClientError("Client returned unexpected response (object missing)")

    torrent_completed = (
      (torrent['state'] == "Paused" and (torrent['progress'] == 100 or not torrent['total_remaining'])) or
      torrent['state'] == "Seeding" or
      torrent['progress'] == 100 or
      not torrent['total_remaining']
    )

    return {
      'complete': torrent_completed,
      'label': torrent.get("label"),
      'save_path': torrent['save_path'],
    }
  
  def __is_label_plugin_enabled(self):
    response = self.__request("core.get_enabled_plugins")

    return "Label" in response

  def __request(self, method, params=[]):
    href, _, _ = self._extract_credentials_from_url(self._rpc_url)

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    if self._deluge_cookie:
      headers["Cookie"] = self._deluge_cookie

    try:
      response = requests.post(
        href,
        json={
          "method": method,
          "params": params,
          "id": self._deluge_request_id,
        },
        headers=headers,
        timeout=10,
      )
      self._deluge_request_id += 1
    except RequestException as network_error:
      if network_error.response and network_error.response.status_code == 408:
        raise TorrentClientError(f"Deluge method {method} timed out after 10 seconds")
      raise TorrentClientError(f"Failed to connect to Deluge at {href}") from network_error

    try:
      json_response = response.json()
    except json.JSONDecodeError as json_parse_error:
      raise TorrentClientError(f"Deluge method {method} response was non-JSON") from json_parse_error

    self.__handle_response_headers(response.headers)

    if "error" in json_response and json_response["error"]:
      raise TorrentClientError(f"Deluge method {method} returned an error: {json_response['error']}")

    return json_response["result"]

  def __handle_response_headers(self, headers):
    if "Set-Cookie" in headers:
      self._deluge_cookie = headers["Set-Cookie"].split(";")[0]
    else:
      self._deluge_cookie = None
