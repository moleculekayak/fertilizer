import json
import requests
from urllib.parse import urlencode
from requests.structures import CaseInsensitiveDict

from ..filesystem import sane_join
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
    response = self.request(f"torrents/info", {"hashes": infohash})

    if response:
      torrent = json.loads(response)[0]
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
      raise TorrentClientError("Failed to get torrent info")

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
  def request(self, path, body = None):
    href, _username, _password = self._qbit_url_parts

    try:
      response = requests.post(
        sane_join(href, path),
        headers=CaseInsensitiveDict({"Cookie": self._qbit_cookie}),
        data=body,
      )

      response.raise_for_status()

      return response.text
    # TODO: handle 403 (and other) errors the same way deluge does
    except requests.RequestException as e:
      return None
