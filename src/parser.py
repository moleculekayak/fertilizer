from hashlib import sha1
from .trackers import RedTracker, OpsTracker

import bencoder

def get_source(torrent_data):
  try:
    return torrent_data[b"info"][b"source"]
  except KeyError:
    return None

def get_announce_url(torrent_data):
  try:
    return torrent_data[b"announce"]
  except KeyError:
    return None

def get_origin_tracker(torrent_data):
  source = get_source(torrent_data) or b""
  announce_url = get_announce_url(torrent_data) or b""

  if source in RedTracker.source_flags() or RedTracker.announce_url() in announce_url:
    return RedTracker
  
  if source in OpsTracker.source_flags() or OpsTracker.announce_url() in announce_url:
    return OpsTracker
  
  return None

def get_new_hash(torrent_data, new_source):
  torrent_data[b"info"][b"source"] = new_source
  hash = sha1(bencoder.encode(torrent_data[b"info"])).hexdigest().upper()

  return hash


def get_torrent_data(filename):
  with open(filename, "rb") as f:
    data = bencoder.decode(f.read())

  return data


def save_torrent_data(filename, torrent_data):
  with open(filename, "wb") as f:
    f.write(bencoder.encode(torrent_data))
