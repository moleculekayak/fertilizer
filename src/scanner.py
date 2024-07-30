import os

from .api import RedAPI, OpsAPI
from .filesystem import mkdir_p, list_files_of_extension, assert_path_exists
from .progress import Progress
from .torrent import generate_new_torrent_from_file
from .parser import get_torrent_data, calculate_infohash
from .errors import TorrentDecodingError, UnknownTrackerError, TorrentNotFoundError, TorrentAlreadyExistsError


def scan_torrent_directory(
  input_directory: str,
  output_directory: str,
  red_api: RedAPI,
  ops_api: OpsAPI,
) -> str:
  """
  Scans a directory for .torrent files and generates new ones using the tracker APIs.

  Args:
    `input_directory` (`str`): The directory containing the .torrent files.
    `output_directory` (`str`): The directory to save the new .torrent files.
    `red_api` (`RedAPI`): The pre-configured RED tracker API.
    `ops_api` (`OpsAPI`): The pre-configured OPS tracker API.
  Returns:
    str: A report of the scan.
  Raises:
    `FileNotFoundError`: if the input directory does not exist.
  """

  input_directory = assert_path_exists(input_directory)
  output_directory = mkdir_p(output_directory)

  input_torrents = list_files_of_extension(input_directory, ".torrent")
  output_torrents = list_files_of_extension(output_directory, ".torrent")
  input_infohashes = __collect_infohashes_from_files(input_torrents)
  output_infohashes = __collect_infohashes_from_files(output_torrents)

  p = Progress(len(input_torrents))

  for i, torrent_path in enumerate(input_torrents, 1):
    basename = os.path.basename(torrent_path)
    print(f"({i}/{p.total}) {basename}")

    try:
      new_tracker, new_torrent_filepath = generate_new_torrent_from_file(
        torrent_path,
        output_directory,
        red_api,
        ops_api,
        input_infohashes,
        output_infohashes,
      )

      p.generated.print(
        f"Found with source '{new_tracker.site_shortname()}' and generated as '{new_torrent_filepath}'."
      )
    except TorrentDecodingError as e:
      p.error.print(str(e))
      continue
    except UnknownTrackerError as e:
      p.skipped.print(str(e))
      continue
    except TorrentAlreadyExistsError as e:
      p.already_exists.print(str(e))
      continue
    except TorrentNotFoundError as e:
      p.not_found.print(str(e))
      continue
    except Exception as e:
      p.error.print(str(e))
      continue

  return p.report()


def __collect_infohashes_from_files(files: list[str]) -> dict:
  infohash_dict = {}

  for filename in files:
    torrent_data = get_torrent_data(filename)

    if torrent_data:
      infohash = calculate_infohash(torrent_data)
      infohash_dict[infohash] = torrent_data[b"info"][b"name"].decode()

  return infohash_dict
