import base64
import json
from enum import Enum
from http import HTTPStatus

import requests

from requests.auth import HTTPBasicAuth
from requests.structures import CaseInsensitiveDict

from ..filesystem import sane_join
from ..parser import get_bencoded_data, calculate_infohash
from ..errors import TorrentClientError, TorrentClientAuthenticationError, TorrentExistsInClientError
from .torrent_client import TorrentClient


class StatusEnum(Enum):
  STOPPED = 0
  QUEUED_VERIFY = 1
  VERIFYING = 2
  QUEUE_DOWNLOAD = 3
  DOWNLOADING = 4
  QUEUED_SEED = 5
  SEEDING = 6


class TransmissionBt(TorrentClient):
  X_TRANSMISSION_SESSION_ID = "X-Transmission-Session-Id"

  def __init__(self, rpc_url):
    super().__init__()
    transmission_url_parts = self._extract_credentials_from_url(rpc_url, "transmission/rpc")
    self._base_url = transmission_url_parts[0]
    self._basic_auth = HTTPBasicAuth(transmission_url_parts[1], transmission_url_parts[2])
    self._transmission_session_id = None

  def setup(self):
    self.__authenticate()
    return self

  def get_torrent_info(self, infohash):
    response = self.__wrap_request(
      "torrent-get",
      arguments={"fields": ["labels", "downloadDir", "percentDone", "status", "doneDate", "name"], "ids": [infohash]},
    )

    if response:
      try:
        parsed_response = json.loads(response)
      except json.JSONDecodeError as json_parse_error:
        raise TorrentClientError("Client returned malformed json response") from json_parse_error

      if not parsed_response.get("arguments", {}).get("torrents", []):
        raise TorrentClientError(f"Torrent not found in client ({infohash})")

      torrent = parsed_response["arguments"]["torrents"][0]
      torrent_completed = (torrent["percentDone"] == 1.0 or torrent["doneDate"] > 0) and torrent["status"] in [
        StatusEnum.SEEDING.value,
        StatusEnum.QUEUED_SEED.value,
      ]

      return {
        "complete": torrent_completed,
        "label": torrent["labels"],
        "save_path": torrent["downloadDir"],
        "content_path": sane_join(torrent["downloadDir"], torrent["name"]),
      }
    else:
      raise TorrentClientError("Client returned unexpected response")

  def inject_torrent(self, source_torrent_infohash, new_torrent_filepath, save_path_override=None):
    source_torrent_info = self.get_torrent_info(source_torrent_infohash)

    if not source_torrent_info["complete"]:
      raise TorrentClientError("Cannot inject a torrent that is not complete")

    new_torrent_infohash = calculate_infohash(get_bencoded_data(new_torrent_filepath)).lower()
    new_torrent_already_exists = self.__does_torrent_exist_in_client(new_torrent_infohash)
    if new_torrent_already_exists:
      raise TorrentExistsInClientError(f"New torrent already exists in client ({new_torrent_infohash})")

    self.__wrap_request(
      "torrent-add",
      arguments={
        "download-dir": save_path_override if save_path_override else source_torrent_info["save_path"],
        "metainfo": base64.b64encode(open(new_torrent_filepath, "rb").read()).decode("utf-8"),
        "labels": source_torrent_info["label"],
      },
    )

    return new_torrent_infohash

  def __authenticate(self):
    try:
      # This method specifically does not use the __wrap_request method
      # because we want to avoid an infinite loop of re-authenticating
      response = requests.post(self._base_url, auth=self._basic_auth)
      # TransmissionBt returns a 409 status code if the session id is invalid
      # (which it is on your first request) and includes a new session id in the response headers.
      if response.status_code == HTTPStatus.CONFLICT:
        self._transmission_session_id = response.headers.get(self.X_TRANSMISSION_SESSION_ID)
      else:
        response.raise_for_status()
    except requests.RequestException as e:
      raise TorrentClientAuthenticationError(f"TransmissionBt login failed: {e}")

    if not self._transmission_session_id:
      raise TorrentClientAuthenticationError("TransmissionBt login failed: Invalid username or password")

  def __wrap_request(self, method, arguments, files=None):
    try:
      return self.__request(method, arguments, files)
    except TorrentClientAuthenticationError:
      self.__authenticate()
      return self.__request(method, arguments, files)

  def __request(self, method, arguments=None, files=None):
    try:
      response = requests.post(
        self._base_url,
        auth=self._basic_auth,
        headers=CaseInsensitiveDict({self.X_TRANSMISSION_SESSION_ID: self._transmission_session_id}),
        json={"method": method, "arguments": arguments},
        files=files,
      )

      response.raise_for_status()

      return response.text
    except requests.RequestException as e:
      if e.response.status_code == HTTPStatus.CONFLICT:
        raise TorrentClientAuthenticationError("Failed to authenticate with TransmissionBt")

      raise TorrentClientError(f"TransmissionBt request to '{self._base_url}' for method '{method}' failed: {e}")

  def __does_torrent_exist_in_client(self, infohash):
    try:
      return bool(self.get_torrent_info(infohash))
    except TorrentClientError:
      return False
