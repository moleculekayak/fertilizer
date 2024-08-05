import json
import base64
import requests
from pathlib import Path
from urllib.parse import urlencode
from requests.structures import CaseInsensitiveDict

from ..filesystem import sane_join
from ..parser import get_bencoded_data, calculate_infohash
from ..errors import TorrentClientError, TorrentClientAuthenticationError
from .torrent_client import TorrentClient


class Qbittorrent(TorrentClient):
  def __init__(self, qbit_url):
    super().__init__()
    self._qbit_url_parts = self._extract_credentials_from_url(qbit_url, "/api/v2")
    self._qbit_cookie = None

  def setup(self):
    self.__authenticate()
    return self

  def get_torrent_info(self, infohash):
    response = self.__request(f"torrents/info", data={"hashes": infohash})

    if response:
      parsed_response = json.loads(response)

      if not parsed_response:
        raise TorrentClientError(f"Torrent not found in client ({infohash})")

      torrent = parsed_response[0]
      torrent_completed = (
        torrent["progress"] == 1.0 or 
        torrent["state"] == "pausedUP" or
        torrent["completion_on"] > 0
      )

      return {
        "complete": torrent_completed,
        "label": torrent["category"],
        "save_path": torrent["save_path"],
        # TODO: do something with this
        "content_path": torrent["content_path"],
      }
    else:
      raise TorrentClientError("Client returned unexpected response")

  def inject_torrent(self, source_torrent_infohash, new_torrent_filepath, save_path_override=None):
    source_torrent_info = self.get_torrent_info(source_torrent_infohash)
    new_torrent_infohash = calculate_infohash(get_bencoded_data(new_torrent_filepath)).lower()
    new_torrent_already_exists = self.__does_torrent_exist_in_client(new_torrent_infohash)

    if new_torrent_already_exists:
      raise TorrentClientError(f"New torrent already exists in client ({new_torrent_infohash})")

    injection_filename = f"{Path(new_torrent_filepath).stem}.fertilizer.torrent"
    torrents = {"torrents": (injection_filename, open(new_torrent_filepath, "rb"), "application/x-bittorrent")}
    params = {
      "autoTMM": False,
      "category": self._determine_label(source_torrent_info),
      "tags": self.torrent_label,
      "savepath": save_path_override if save_path_override else source_torrent_info["save_path"],
    }

    self.__request("torrents/add", data=params, files=torrents)

    return new_torrent_infohash

  def __authenticate(self):
    href, username, password = self._qbit_url_parts

    try:
      if username or password:
        payload = urlencode({"username": username, "password": password})
      else:
        payload = {}

      response = requests.post(f"{href}/auth/login", data=payload)
      response.raise_for_status()
    except requests.RequestException as e:
      raise TorrentClientAuthenticationError(f"qBittorrent login failed: {e}")

    self._qbit_cookie = response.cookies.get_dict().get("SID")
    if not self._qbit_cookie:
      raise TorrentClientAuthenticationError("qBittorrent login failed: Invalid username or password")

  # TODO: wrap this like I did with deluge
  def __request(self, path, data = None, files = None):
    href, _username, _password = self._qbit_url_parts

    try:
      response = requests.post(
        sane_join(href, path),
        headers=CaseInsensitiveDict({"Cookie": self._qbit_cookie}),
        data=data,
        files=files,
      )

      response.raise_for_status()

      return response.text
    # TODO: handle 403 (and other) errors the same way deluge does
    except requests.RequestException as e:
      return None

  def __does_torrent_exist_in_client(self, infohash):
    try:
      return bool(self.get_torrent_info(infohash))
    except TorrentClientError as e:
      return False
