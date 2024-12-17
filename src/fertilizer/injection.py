import os
import shutil

from .clients.deluge import Deluge
from .clients.qbittorrent import Qbittorrent
from .clients.transmission import TransmissionBt
from .config import Config
from .errors import TorrentInjectionError
from .parser import calculate_infohash, get_bencoded_data


class Injection:
  def __init__(self, config: Config):
    self.config = self.__validate_config(config)
    self.linking_directory = config.injection_link_directory
    self.client = self.__determine_torrent_client(config)

  def setup(self):
    self.client.setup()
    return self

  def inject_torrent(self, source_torrent_filepath, new_torrent_filepath, new_tracker):
    source_torrent_data = get_bencoded_data(source_torrent_filepath)
    source_torrent_file_or_dir = self.__determine_source_torrent_data_location(source_torrent_data)
    output_location = self.__determine_output_location(source_torrent_file_or_dir, new_tracker)
    self.__link_files_to_output_location(source_torrent_file_or_dir, output_location)
    output_parent_directory = os.path.dirname(os.path.normpath(output_location))

    return self.client.inject_torrent(
      calculate_infohash(source_torrent_data),
      new_torrent_filepath,
      save_path_override=output_parent_directory,
    )

  @staticmethod
  def __validate_config(config: Config):
    if not config.inject_torrents:
      raise TorrentInjectionError("Torrent injection is disabled in the config file.")

    if not config.injection_link_directory:
      raise TorrentInjectionError("No injection link directory specified in the config file.")

    if (not config.deluge_rpc_url) and (not config.transmission_rpc_url) and (not config.qbittorrent_url):
      raise TorrentInjectionError("No torrent client configuration specified in the config file.")

    return config

  @staticmethod
  def __determine_torrent_client(config: Config):
    if config.deluge_rpc_url:
      return Deluge(config.deluge_rpc_url)
    elif config.transmission_rpc_url:
      return TransmissionBt(config.transmission_rpc_url)
    elif config.qbittorrent_url:
      return Qbittorrent(config.qbittorrent_url)

  # If the torrent is a single bare file, this returns the path _to that file_
  # If the torrent is one or many files in a directory, this returns the topmost directory path
  def __determine_source_torrent_data_location(self, torrent_data):
    # Note on torrent file structures:
    # --------
    # From my testing, all torrents have a `name` stored at `[b"info"][b"name"]`. This appears to always
    # be the name of the top-most file or directory that contains torrent data. Although I've always seen
    # the name key, apparently it is only a suggestion so we add checks to verify existence of the file/directory
    # (although we do nothing to try and recover if that file/directory is missing)
    #
    # So if the torrent is a single file, the `name` is the full filename of that file, including extension.
    # If the torrent contains a directory, the `name` is the name of that directory and the subfiles of the
    # torrents are stored under that directory.
    #
    # If a torrent has one file and that file is at the root level of the torrent, the `files` key is absent.
    # If a torrent has multiple files OR a single file, but it's in a directory, the `files` key is present
    # and is an array of dictionaries. Each dictionary has a `path` key that is an array of bytestrings where
    # each array member is a part of the path to the file. In other words, if you joined all the bytestrings
    # in the `path` array for a given file, you'd get the path to the file relative to the topmost parent
    # directory (which in our case is the `name`).
    #
    # See also: https://en.wikipedia.org/wiki/Torrent_file#File_struct
    infohash = calculate_infohash(torrent_data)
    torrent_info_from_client = self.client.get_torrent_info(infohash)
    proposed_torrent_data_location = torrent_info_from_client["content_path"]

    if os.path.exists(proposed_torrent_data_location):
      return proposed_torrent_data_location

    raise TorrentInjectionError(
      f"Could not determine the location of the torrent data: {proposed_torrent_data_location}"
    )

  def __determine_output_location(self, source_torrent_file_or_dir, new_tracker):
    tracker_output_directory = os.path.join(self.linking_directory, new_tracker)
    os.makedirs(tracker_output_directory, exist_ok=True)

    return os.path.join(tracker_output_directory, os.path.basename(source_torrent_file_or_dir))

  @staticmethod
  def __link_files_to_output_location(source_torrent_file_or_dir, output_location):
    if os.path.exists(output_location):
      raise TorrentInjectionError(f"Cannot link given torrent since it's already been linked: {output_location}")

    if os.path.isfile(source_torrent_file_or_dir):
      os.link(source_torrent_file_or_dir, output_location)
    elif os.path.isdir(source_torrent_file_or_dir):
      shutil.copytree(source_torrent_file_or_dir, output_location, copy_function=os.link)

    return output_location
