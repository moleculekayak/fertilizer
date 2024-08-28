import json
import base64
import requests
from pathlib import Path

from ..filesystem import sane_join
from ..parser import get_bencoded_data, calculate_infohash
from ..errors import TorrentClientError, TorrentClientAuthenticationError, TorrentExistsInClientError
from .torrent_client import TorrentClient
from requests.exceptions import RequestException
from requests.structures import CaseInsensitiveDict


class Deluge(TorrentClient):
  ERROR_CODES = {
    "NO_AUTH": 1,
  }

  def __init__(self, rpc_url):
    super().__init__()
    self._rpc_url = rpc_url
    self._deluge_cookie = None
    self._deluge_request_id = 0
    self._label_plugin_enabled = False

  def setup(self):
    connection_response = self.__authenticate()
    self._label_plugin_enabled = self.__is_label_plugin_enabled()

    return connection_response

  def get_torrent_info(self, infohash):
    infohash = infohash.lower()
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

    response = self.__wrap_request("web.update_ui", params)
    if "torrents" in response:
      torrent = response["torrents"].get(infohash)

      if torrent is None:
        raise TorrentClientError(f"Torrent not found in client ({infohash})")
    else:
      raise TorrentClientError("Client returned unexpected response (object missing)")

    torrent_completed = (
      (torrent["state"] == "Paused" and (torrent["progress"] == 100 or not torrent["total_remaining"]))
      or torrent["state"] == "Seeding"
      or torrent["progress"] == 100
      or not torrent["total_remaining"]
    )

    return {
      "complete": torrent_completed,
      "label": torrent.get("label"),
      "save_path": torrent["save_path"],
      "content_path": sane_join(torrent["save_path"], torrent["name"]),
    }

  def inject_torrent(self, source_torrent_infohash, new_torrent_filepath, save_path_override=None):
    new_torrent_infohash = calculate_infohash(get_bencoded_data(new_torrent_filepath)).lower()
    new_torrent_already_exists = self.__does_torrent_exist_in_client(new_torrent_infohash)

    if new_torrent_already_exists:
      raise TorrentExistsInClientError(f"New torrent already exists in client ({new_torrent_infohash})")

    source_torrent_info = self.get_torrent_info(source_torrent_infohash)

    if not source_torrent_info["complete"]:
      raise TorrentClientError("Cannot inject a torrent that is not complete")

    params = [
      f"{Path(new_torrent_filepath).stem}.fertilizer.torrent",
      base64.b64encode(open(new_torrent_filepath, "rb").read()).decode("utf-8"),
      {
        "download_location": save_path_override if save_path_override else source_torrent_info["save_path"],
        "seed_mode": True,
        "add_paused": False,
      },
    ]

    new_torrent_infohash = self.__wrap_request("core.add_torrent_file", params)
    newtorrent_label = self._determine_label(source_torrent_info)
    self.__set_label(new_torrent_infohash, newtorrent_label)

    return new_torrent_infohash

  def __authenticate(self):
    _href, _username, password = self._extract_credentials_from_url(self._rpc_url)
    if not password:
      raise Exception("You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112)")

    # This method specifically cannot use __wrap_request because an auth error would create an infinite loop
    auth_response = self.__request("auth.login", [password])
    if not auth_response:
      raise TorrentClientError("Reached Deluge RPC endpoint but failed to authenticate")

    return self.__request("web.connected")

  def __is_label_plugin_enabled(self):
    response = self.__wrap_request("core.get_enabled_plugins")

    return "Label" in response

  def __set_label(self, infohash, label):
    if not self._label_plugin_enabled:
      return

    current_labels = self.__wrap_request("label.get_labels")
    if label not in current_labels:
      self.__wrap_request("label.add", [label])

    return self.__wrap_request("label.set_torrent", [infohash, label])

  def __wrap_request(self, method, params=[]):
    try:
      return self.__request(method, params)
    except TorrentClientAuthenticationError:
      self.__authenticate()
      return self.__request(method, params)

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
      if json_response["error"]["code"] == self.ERROR_CODES["NO_AUTH"]:
        raise TorrentClientAuthenticationError("Failed to authenticate with Deluge")
      raise TorrentClientError(f"Deluge method {method} returned an error: {json_response['error']['message']}")

    return json_response["result"]

  def __handle_response_headers(self, headers):
    if "Set-Cookie" in headers:
      self._deluge_cookie = headers["Set-Cookie"].split(";")[0]

  def __does_torrent_exist_in_client(self, infohash):
    try:
      return bool(self.get_torrent_info(infohash))
    except TorrentClientError:
      return False
