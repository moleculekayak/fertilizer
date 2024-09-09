import copy
import os
from html import unescape

from .api import RedAPI, OpsAPI
from .errors import TorrentDecodingError, UnknownTrackerError, TorrentNotFoundError, TorrentAlreadyExistsError
from .filesystem import replace_extension
from .parser import (
  get_bencoded_data,
  get_origin_tracker,
  recalculate_hash_for_new_source,
  save_bencoded_data,
)
from .trackers import RedTracker, OpsTracker


def generate_new_torrent_from_file(
  source_torrent_path: str,
  output_directory: str,
  red_api: RedAPI,
  ops_api: OpsAPI,
  input_infohashes=None,
  output_infohashes=None,
) -> tuple[OpsTracker | RedTracker, str, bool]:
  """
  Generates a new torrent file for the reciprocal tracker of the original torrent file if it exists on the reciprocal tracker.

  Args:
    `source_torrent_path` (`str`): The path to the original torrent file.
    `output_directory` (`str`): The directory to save the new torrent file.
    `red_api` (`RedApi`): The pre-configured API object for RED.
    `ops_api` (`OpsApi`): The pre-configured API object for OPS.
    `input_infohashes` (`dict`, optional): A dictionary of infohashes and their filenames from the input directory for caching purposes. Defaults to an empty dictionary.
    `output_infohashes` (`dict`, optional): A dictionary of infohashes and their filenames from the output directory for caching purposes. Defaults to an empty dictionary.
  Returns:
    A tuple containing the new tracker class (`RedTracker` or `OpsTracker`), the path to the new torrent file, and a boolean
    representing whether the torrent already existed (False: created just now, True: torrent file already existed).
  Raises:
    `TorrentDecodingError`: if the original torrent file could not be decoded.
    `UnknownTrackerError`: if the original torrent file is not from OPS or RED.
    `TorrentNotFoundError`: if the original torrent file could not be found on the reciprocal tracker.
    `TorrentAlreadyExistsError`: if the new torrent file already exists in the input or output directory.
    `Exception`: if an unknown error occurs.
  """

  if output_infohashes is None:
    output_infohashes = {}
  if input_infohashes is None:
    input_infohashes = {}
  source_torrent_data, source_tracker = __get_bencoded_data_and_tracker(source_torrent_path)
  new_torrent_data = copy.deepcopy(source_torrent_data)
  new_tracker = source_tracker.reciprocal_tracker()
  new_tracker_api = __get_new_tracker_api(new_tracker, red_api, ops_api)
  stored_api_response = None

  all_possible_hashes = __calculate_all_possible_hashes(source_torrent_data, new_tracker.source_flags_for_creation())
  found_input_hash = __check_matching_hashes(all_possible_hashes, input_infohashes)
  found_output_hash = __check_matching_hashes(all_possible_hashes, output_infohashes)

  if found_input_hash:
    raise TorrentAlreadyExistsError(
      f"Torrent already exists in input directory at {input_infohashes[found_input_hash]}"
    )
  if found_output_hash:
    return new_tracker, output_infohashes[found_output_hash], True

  for new_source in new_tracker.source_flags_for_creation():
    new_hash = recalculate_hash_for_new_source(source_torrent_data, new_source)
    stored_api_response = new_tracker_api.find_torrent(new_hash)

    if stored_api_response["status"] == "success":
      new_torrent_filepath = __generate_torrent_output_filepath(
        stored_api_response,
        new_tracker,
        new_source.decode("utf-8"),
        output_directory,
      )

      if os.path.exists(new_torrent_filepath):
        return new_tracker, new_torrent_filepath, True

      if new_torrent_filepath:
        torrent_id = __get_torrent_id(stored_api_response)

        new_torrent_data[b"info"][b"source"] = new_source  # This is already bytes rather than str
        new_torrent_data[b"announce"] = new_tracker_api.announce_url.encode()
        new_torrent_data[b"comment"] = __generate_torrent_url(new_tracker_api.site_url, torrent_id).encode()
        save_bencoded_data(new_torrent_filepath, new_torrent_data)

        return new_tracker, new_torrent_filepath, False

  if stored_api_response["error"] in ("bad hash parameter", "bad parameters"):
    raise TorrentNotFoundError(f"Torrent could not be found on {new_tracker.site_shortname()}")

  raise Exception(f"An unknown error occurred in the API response from {new_tracker.site_shortname()}")


def __calculate_all_possible_hashes(source_torrent_data: dict, sources: list[str]) -> list[str]:
  return [recalculate_hash_for_new_source(source_torrent_data, source) for source in sources]


def __check_matching_hashes(all_possible_hashes: list[str], infohashes: dict) -> str | None:
  for hash in all_possible_hashes:
    if hash in infohashes:
      return hash

  return None


def __generate_torrent_output_filepath(
  api_response: dict,
  new_tracker: OpsTracker | RedTracker,
  new_source: str,
  output_directory: str,
) -> str:
  tracker_name = new_tracker.site_shortname()
  source_name = f" [{new_source}]" if new_source else ""

  filepath_from_api_response = unescape(api_response["response"]["torrent"]["filePath"])
  filename = f"{filepath_from_api_response}{source_name}.torrent"
  torrent_filepath = os.path.join(output_directory, tracker_name, filename)

  return torrent_filepath


def __get_torrent_id(api_response: dict) -> str:
  return api_response["response"]["torrent"]["id"]


def __generate_torrent_url(site_url: str, torrent_id: str) -> str:
  return f"{site_url}/torrents.php?torrentid={torrent_id}"


def __get_bencoded_data_and_tracker(torrent_path):
  # The fastresume stuff is to support qBittorrent since it doesn't store
  # announce URLs in the torrent file IFF we're taking the file from `BT_backup`.
  #
  # qbit stores that information in a sidecar file that has the exact same name
  # as the torrent file but with a `.fastresume` extension instead. It's also stored
  # in a list of lists called `trackers` in this `.fastresume` file instead of `announce`.
  fastresume_path = replace_extension(torrent_path, ".fastresume")
  source_torrent_data = get_bencoded_data(torrent_path)
  fastresume_data = get_bencoded_data(fastresume_path)

  if not source_torrent_data or not source_torrent_data.get(b"info"):
    raise TorrentDecodingError("Error decoding torrent file")

  torrent_tracker = get_origin_tracker(source_torrent_data)
  fastresume_tracker = get_origin_tracker(fastresume_data) if fastresume_data else None
  source_tracker = torrent_tracker or fastresume_tracker

  if not source_tracker:
    raise UnknownTrackerError("Torrent not from OPS or RED based on source or announce URL")

  return source_torrent_data, source_tracker


def __get_new_tracker_api(new_tracker, red_api, ops_api):
  if new_tracker == RedTracker:
    return red_api

  return ops_api
