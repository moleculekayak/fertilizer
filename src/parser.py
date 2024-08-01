import copy
import bencoder
from hashlib import sha1

from .trackers import RedTracker, OpsTracker


def is_valid_infohash(infohash: str) -> bool:
  if not isinstance(infohash, str) or len(infohash) != 40:
    return False
  try:
    return bool(int(infohash, 16))
  except ValueError:
    return False


def get_source(torrent_data: dict) -> bytes:
  try:
    return torrent_data[b"info"][b"source"]
  except KeyError:
    return None


# TODO: test
def get_name(torrent_data: dict) -> bytes:
  try:
    return torrent_data[b"info"][b"name"]
  except KeyError:
    return None


def get_announce_url(torrent_data: dict) -> bytes:
  try:
    return torrent_data[b"announce"]
  except KeyError:
    return None


def get_origin_tracker(torrent_data: dict) -> RedTracker | OpsTracker | None:
  source = get_source(torrent_data) or b""
  announce_url = get_announce_url(torrent_data) or b""

  if source in RedTracker.source_flags_for_search() or RedTracker.announce_url() in announce_url:
    return RedTracker

  if source in OpsTracker.source_flags_for_search() or OpsTracker.announce_url() in announce_url:
    return OpsTracker

  return None


def calculate_infohash(torrent_data: dict) -> str:
  return sha1(bencoder.encode(torrent_data[b"info"])).hexdigest().upper()


def recalculate_hash_for_new_source(torrent_data: dict, new_source: (bytes | str)) -> str:
  torrent_data = copy.deepcopy(torrent_data)
  torrent_data[b"info"][b"source"] = new_source

  return calculate_infohash(torrent_data)


def get_torrent_data(filename: str) -> dict:
  try:
    with open(filename, "rb") as f:
      data = bencoder.decode(f.read())
    return data
  except Exception:
    return None


def save_torrent_data(filename: str, torrent_data: dict) -> str:
  with open(filename, "wb") as f:
    f.write(bencoder.encode(torrent_data))

  return filename
