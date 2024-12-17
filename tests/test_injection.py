import os
import pytest

from unittest.mock import MagicMock

from .helpers import get_torrent_path, get_support_file_path, copy_and_mkdir, SetupTeardown

from fertilizer.clients.deluge import Deluge
from fertilizer.clients.qbittorrent import Qbittorrent
from fertilizer.clients.transmission import TransmissionBt
from fertilizer.errors import TorrentInjectionError
from fertilizer.injection import Injection


class ConfigMock:
  def __init__(self):
    self.inject_torrents = True
    self.injection_link_directory = "/tmp/injection"
    self.deluge_rpc_url = "http://:pass@localhost:8112/json"
    self.transmission_rpc_url = "http://:pass@localhost:51413/transmission/rpc"
    self.qbittorrent_url = "http://localhost:8080"


@pytest.fixture
def injector():
  instance = Injection(ConfigMock())
  instance.client = MagicMock()
  return instance


class TestInjection(SetupTeardown):
  def test_raises_error_if_injection_disabled(self):
    config = ConfigMock()
    config.inject_torrents = False

    with pytest.raises(TorrentInjectionError) as excinfo:
      Injection(config)

    assert str(excinfo.value) == "Torrent injection is disabled in the config file."

  def test_raises_error_if_no_injection_link_directory(self):
    config = ConfigMock()
    config.injection_link_directory = None

    with pytest.raises(TorrentInjectionError) as excinfo:
      Injection(config)

    assert str(excinfo.value) == "No injection link directory specified in the config file."

  def test_raises_error_if_no_torrent_client_configuration(self):
    config = ConfigMock()
    config.deluge_rpc_url = None
    config.qbittorrent_url = None
    config.transmission_rpc_url = None

    with pytest.raises(TorrentInjectionError) as excinfo:
      Injection(config)

    assert str(excinfo.value) == "No torrent client configuration specified in the config file."

  def test_determines_torrent_client(self):
    # NOTE: I probably should refactor this
    deluge_config = ConfigMock()
    deluge_config.qbittorrent_url = None
    deluge_config.transmission_rpc_url = None

    qbit_config = ConfigMock()
    qbit_config.deluge_rpc_url = None
    qbit_config.transmission_rpc_url = None

    transmission_config = ConfigMock()
    transmission_config.deluge_rpc_url = None
    transmission_config.qbittorrent_url = None

    assert isinstance(Injection(deluge_config).client, Deluge)
    assert isinstance(Injection(qbit_config).client, Qbittorrent)
    assert isinstance(Injection(transmission_config).client, TransmissionBt)


class TestSetup(SetupTeardown):
  def test_calls_torrent_client_setup(self, injector):
    injector.client.setup.assert_not_called()

    injector.setup()

    injector.client.setup.assert_called_once()

  def test_returns_self_after_setup(self, injector):
    assert injector.setup() == injector


class TestInjectTorrent(SetupTeardown):
  def test_injects_torrent_and_returns_infohash(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    copy_and_mkdir(get_support_file_path("foo.txt"), "/tmp/input/Big Buck Bunny/foo.txt")
    injector.client.inject_torrent.return_value = "abc123"
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    result = injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "OPS")

    assert result == "abc123"
    injector.client.inject_torrent.assert_called_with(
      "F15A59B9620FBF4CB06407C10399607367D9204D",
      "/tmp/output/ops_source.torrent",
      save_path_override="/tmp/injection/OPS",
    )

  def test_copies_torrent_files_to_linking_directory(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    copy_and_mkdir(get_support_file_path("foo.txt"), "/tmp/input/Big Buck Bunny/foo.txt")
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "OPS")

    assert os.path.exists("/tmp/injection/OPS/Big Buck Bunny/foo.txt")
    assert os.stat("/tmp/injection/OPS/Big Buck Bunny/foo.txt").st_nlink > 1

  def test_links_torrent_data_when_singular_file(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    # This is a singular file, not a directory
    copy_and_mkdir(get_support_file_path("foo.txt"), "/tmp/input/Big Buck Bunny")
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "OPS")

    assert os.path.exists("/tmp/input/Big Buck Bunny")
    assert os.stat("/tmp/input/Big Buck Bunny").st_nlink > 1
    assert os.path.isfile("/tmp/injection/OPS/Big Buck Bunny")

  def test_uses_tracker_name_in_output_directory(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    copy_and_mkdir(get_support_file_path("foo.txt"), "/tmp/input/Big Buck Bunny/foo.txt")
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "TRACKER")

    assert os.path.exists("/tmp/injection/TRACKER/Big Buck Bunny/foo.txt")

  def test_raises_error_if_input_files_missing(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    with pytest.raises(TorrentInjectionError) as excinfo:
      injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "OPS")

    assert str(excinfo.value) == "Could not determine the location of the torrent data: /tmp/input/Big Buck Bunny"

  def test_raises_error_if_output_directory_exists(self, injector):
    source_torrent_filepath = copy_and_mkdir(get_torrent_path("red_source"), "/tmp/input/red_source.torrent")
    new_torrent_filepath = copy_and_mkdir(get_torrent_path("ops_source"), "/tmp/output/ops_source.torrent")
    parent_dir = "/tmp/injection/OPS/Big Buck Bunny"

    copy_and_mkdir(get_support_file_path("foo.txt"), "/tmp/input/Big Buck Bunny/foo.txt")
    injector.client.get_torrent_info.return_value = {"content_path": "/tmp/input/Big Buck Bunny"}

    os.makedirs(parent_dir)

    with pytest.raises(TorrentInjectionError) as excinfo:
      injector.inject_torrent(source_torrent_filepath, new_torrent_filepath, "OPS")

    assert str(excinfo.value) == f"Cannot link given torrent since it's already been linked: {parent_dir}"
