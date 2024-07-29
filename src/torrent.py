import os
import copy
from html import unescape

from .trackers import RedTracker, OpsTracker
from .api import RedAPI, OpsAPI
from .errors import TorrentDecodingError, UnknownTrackerError, TorrentNotFoundError, TorrentAlreadyExistsError
from .trackers import RedTracker
from .parser import get_torrent_data, get_origin_tracker, recalculate_hash_for_new_source, save_torrent_data

def generate_new_torrent_from_file(
    old_torrent_path: str, 
    output_directory: str, 
    red_api: RedAPI, 
    ops_api: OpsAPI
) -> tuple[OpsTracker | RedTracker, str]:
  """
  Generates a new torrent file for the reciprocal tracker of the original torrent file if it exists on the reciprocal tracker.

  Args:
    `old_torrent_path` (`str`): The path to the original torrent file.
    `output_directory` (`str`): The directory to save the new torrent file.
    `red_api` (`RedApi`): The pre-configured API object for RED.
    `ops_api` (`OpsApi`): The pre-configured API object for OPS.
  Returns:
    A tuple containing the new tracker class (`RedTracker` or `OpsTracker`) and the path to the new torrent file.
  Raises:
    `TorrentDecodingError`: if the original torrent file could not be decoded.
    `UnknownTrackerError`: if the original torrent file is not from OPS or RED.
    `TorrentNotFoundError`: if the original torrent file could not be found on the reciprocal tracker.
    `TorrentAlreadyExistsError`: if the new torrent file already exists in the output directory.
    `Exception`: if an unknown error occurs.
  """

  old_torrent_data, old_tracker = __get_torrent_data_and_tracker(old_torrent_path)
  new_torrent_data = copy.deepcopy(old_torrent_data)
  new_tracker = old_tracker.reciprocal_tracker()
  new_tracker_api = __get_reciprocal_tracker_api(new_tracker, red_api, ops_api)

  for new_source in new_tracker.source_flags_for_creation():
    new_hash = recalculate_hash_for_new_source(old_torrent_data, new_source)
    api_response = new_tracker_api.find_torrent(new_hash)

    if api_response["status"] == "success":
      new_torrent_filepath = generate_torrent_output_filepath(api_response, new_source.decode("utf-8"), output_directory)

      if new_torrent_filepath:
        torrent_id = get_torrent_id(api_response)

        new_torrent_data[b"info"][b"source"] = new_source # This is already bytes rather than str
        new_torrent_data[b"announce"] = new_tracker_api.announce_url.encode()
        new_torrent_data[b"comment"] = generate_torrent_url(new_tracker_api.site_url, torrent_id).encode()

        return (new_tracker, save_torrent_data(new_torrent_filepath, new_torrent_data))
    elif api_response["error"] in ("bad hash parameter", "bad parameters"):
      raise TorrentNotFoundError(f"Torrent could not be found on {new_tracker.site_shortname()}")
    else:
      raise Exception(f"An unknown error occurred in the API response from {new_tracker.site_shortname()}")

def generate_torrent_output_filepath(api_response: dict, new_source: str, output_directory: str) -> str:
    """
    Generates the output filepath for the new torrent file. Does not create the file.

    Args:
      `api_response` (`dict`): The response from the tracker API.
      `new_source` (`str`): The source of the new torrent file (`"RED"` or `"OPS"`).
      `output_directory` (`str`): The directory to save the new torrent file.
    Returns:
      The path to the new torrent file.
    Raises:
      `TorrentAlreadyExistsError`: if the new torrent file already exists in the output directory.
    """

    filepath_from_api_response = unescape(api_response["response"]["torrent"]["filePath"])
    filename = f'{filepath_from_api_response} [{new_source}].torrent'
    torrent_filepath = os.path.join(output_directory, filename)

    if os.path.isfile(torrent_filepath):
      raise TorrentAlreadyExistsError(f"Torrent file already exists at {torrent_filepath}")

    return torrent_filepath

def get_torrent_id(api_response: dict) -> str:
  """
  Extracts the torrent ID from the API response.

  Args:
    `api_response` (`dict`): The response from the tracker API.
  Returns:
    The torrent ID.
  """

  return api_response["response"]["torrent"]["id"]

def generate_torrent_url(site_url: str, torrent_id: str) -> str:
  """
  Generates the URL to the torrent on the tracker.

  Args:
    `site_url` (`str`): The base URL of the tracker.
    `torrent_id` (`str`): The ID of the torrent.
  Returns:
    The URL to the torrent.
  """

  return f"{site_url}/torrents.php?torrentid={torrent_id}"

def __get_torrent_data_and_tracker(torrent_path):
  old_torrent_data = get_torrent_data(torrent_path)
  
  if not old_torrent_data:
    raise TorrentDecodingError("Error decoding torrent file")

  old_tracker = get_origin_tracker(old_torrent_data)

  if not old_tracker:
    raise UnknownTrackerError("Torrent not from OPS or RED based on source or announce URL")

  return old_torrent_data, old_tracker

def __get_reciprocal_tracker_api(new_tracker, red_api, ops_api):
  return red_api if new_tracker == RedTracker else ops_api
