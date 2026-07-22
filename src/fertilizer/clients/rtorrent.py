import xmlrpc.client

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from ..filesystem import sane_join
from ..parser import get_bencoded_data, calculate_infohash
from ..errors import TorrentClientError, TorrentClientAuthenticationError, TorrentExistsInClientError
from .torrent_client import TorrentClient


class RTorrent(TorrentClient):
  # rTorrent's native transport is SCGI, but it is almost always fronted by an
  # HTTP XMLRPC endpoint (ruTorrent's RPC2 mount, flood, or an nginx SCGIMount).
  # We speak that HTTP XMLRPC over requests, like every other client here, so the
  # config URL looks the same: http(s)://[user:pass@]host[:port]/RPC2
  #
  # rTorrent identifies torrents by an UPPERCASE hex infohash and stores the
  # ruTorrent-style label in d.custom1.
  def __init__(self, rpc_url):
    super().__init__()
    href, username, password = self._extract_credentials_from_url(rpc_url)
    self._url = href
    self._basic_auth = HTTPBasicAuth(username, password) if (username or password) else None

  def setup(self):
    # A cheap round-trip every rTorrent build supports; also proves the HTTP
    # XMLRPC endpoint is reachable and authenticated.
    version = self.__request("system.client_version")
    if not version:
      raise TorrentClientError("Reached the rTorrent RPC endpoint but got no version back")
    return version

  def get_torrent_info(self, infohash):
    infohash = infohash.upper()

    try:
      complete = self.__request("d.complete", infohash)
      directory = self.__request("d.directory", infohash)
      base_path = self.__request("d.base_path", infohash)
      name = self.__request("d.name", infohash)
      label = self.__request("d.custom1", infohash)
    except TorrentClientError as not_found_error:
      # rTorrent raises a fault (mapped to TorrentClientError) for an unknown hash.
      raise TorrentClientError(f"Torrent not found in client ({infohash})") from not_found_error

    return {
      "complete": bool(int(complete)),
      "label": label or None,
      "save_path": directory,
      "content_path": base_path or sane_join(directory, name),
    }

  def inject_torrent(self, source_torrent_infohash, new_torrent_filepath, save_path_override=None):
    new_torrent_infohash = calculate_infohash(get_bencoded_data(new_torrent_filepath)).upper()

    if self.__does_torrent_exist_in_client(new_torrent_infohash):
      raise TorrentExistsInClientError(f"New torrent already exists in client ({new_torrent_infohash})")

    source_torrent_info = self.get_torrent_info(source_torrent_infohash)
    if not source_torrent_info["complete"]:
      raise TorrentClientError("Cannot inject a torrent that is not complete")

    save_path = save_path_override if save_path_override else source_torrent_info["save_path"]
    newtorrent_label = self._determine_label(source_torrent_info)

    with open(new_torrent_filepath, "rb") as torrent_file:
      torrent_data = xmlrpc.client.Binary(torrent_file.read())

    # load.raw_start: (target, raw torrent bytes, *commands run before start). The
    # commands set the data directory and the label (d.custom1) before the hash
    # check, so the files fertilizer just linked are found and the torrent seeds.
    self.__request(
      "load.raw_start",
      "",
      torrent_data,
      f"d.directory.set={save_path}",
      f"d.custom1.set={newtorrent_label}",
    )

    return new_torrent_infohash.lower()

  def __does_torrent_exist_in_client(self, infohash):
    try:
      return bool(self.get_torrent_info(infohash))
    except TorrentClientError:
      return False

  def __request(self, method, *params):
    xml_body = xmlrpc.client.dumps(tuple(params), method)

    try:
      response = requests.post(
        self._url,
        data=xml_body,
        headers={"Content-Type": "text/xml"},
        auth=self._basic_auth,
        timeout=10,
      )
    except RequestException as network_error:
      raise TorrentClientError(f"Failed to connect to rTorrent at {self._url}") from network_error

    if response.status_code == 401:
      raise TorrentClientAuthenticationError("Failed to authenticate with rTorrent")
    if response.status_code != 200:
      raise TorrentClientError(f"rTorrent method {method} returned HTTP {response.status_code}")

    try:
      result, _method_name = xmlrpc.client.loads(response.content)
    except xmlrpc.client.Fault as fault:
      raise TorrentClientError(f"rTorrent method {method} returned a fault: {fault.faultString}") from fault
    except Exception as parse_error:
      raise TorrentClientError(f"rTorrent method {method} returned a non-XMLRPC response") from parse_error

    return result[0] if result else None
