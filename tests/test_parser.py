import os

from .support import get_torrent_path, SetupTeardown

from src.trackers import RedTracker, OpsTracker
from src.parser import (
  get_source,
  get_torrent_data,
  get_announce_url,
  get_origin_tracker,
  recalculate_hash_for_new_source,
  save_torrent_data,
)


class TestParserGetSource(SetupTeardown):
  def test_returns_source_if_present(self):
    assert get_source({b"info": {b"source": b"FOO"}}) == b"FOO"

  def test_returns_none_if_absent(self):
    assert get_source({}) is None


class TestParserGetAnnounceUrl(SetupTeardown):
  def test_returns_url_if_present(self):
    assert get_announce_url({b"announce": b"https://foo.bar"}) == b"https://foo.bar"

  def test_returns_none_if_absent(self):
    assert get_announce_url({}) is None


class TestParserGetOriginTracker(SetupTeardown):
  def test_returns_red_based_on_source(self):
    assert get_origin_tracker({b"info": {b"source": b"RED"}}) == RedTracker
    assert get_origin_tracker({b"info": {b"source": b"PTH"}}) == RedTracker

  def test_returns_ops_based_on_source(self):
    assert get_origin_tracker({b"info": {b"source": b"OPS"}}) == OpsTracker

  def test_returns_red_based_on_announce(self):
    assert get_origin_tracker({b"announce": b"https://flacsfor.me/123abc"}) == RedTracker

  def test_returns_ops_based_on_announce(self):
    assert get_origin_tracker({b"announce": b"https://home.opsfet.ch/123abc"}) == OpsTracker

  def test_returns_none_if_no_match(self):
    assert get_origin_tracker({}) is None
    assert get_origin_tracker({b"info": {b"source": b"FOO"}}) is None
    assert get_origin_tracker({b"announce": b"https://foo/123abc"}) is None


class TestParserReplaceSourceAndReturnHash(SetupTeardown):
  def test_replaces_source_and_returns_hash(self):
    torrent_data = {b"info": {b"source": b"RED"}}
    new_source = b"OPS"

    result = recalculate_hash_for_new_source(torrent_data, new_source)

    assert result == "4F36F59992B6F7CB6EB6C2DEE06DD66AC81A981B"

  def test_doesnt_mutate_original_dict(self):
    torrent_data = {b"info": {b"source": b"RED"}}
    new_source = b"OPS"

    recalculate_hash_for_new_source(torrent_data, new_source)

    assert torrent_data == {b"info": {b"source": b"RED"}}


class TestParserGetTorrentData(SetupTeardown):
  def test_returns_torrent_data(self):
    result = get_torrent_data(get_torrent_path("no_source"))

    assert isinstance(result, dict)
    assert b"info" in result

  def test_returns_none_on_error(self):
    result = get_torrent_data(get_torrent_path("broken"))

    assert result is None


class TestParserSaveTorrentData(SetupTeardown):
  def test_saves_torrent_data(self):
    torrent_data = {b"info": {b"source": b"RED"}}
    filename = "/tmp/test_save_torrent_data.torrent"

    save_torrent_data(filename, torrent_data)

    with open(filename, "rb") as f:
      result = f.read()

    assert result == b"d4:infod6:source3:REDee"

    os.remove(filename)

  def test_returns_filename(self):
    torrent_data = {b"info": {b"source": b"RED"}}
    filename = "/tmp/test_save_torrent_data.torrent"

    result = save_torrent_data(filename, torrent_data)

    assert result == filename

    os.remove(filename)
