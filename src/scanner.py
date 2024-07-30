import os

from .api import RedAPI, OpsAPI
from .filesystem import mkdir_p, list_files_of_extension, assert_path_exists
from .progress import Progress
from .torrent import generate_new_torrent_from_file
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
  local_torrents = list_files_of_extension(input_directory, ".torrent")
  p = Progress(len(local_torrents))

  for i, torrent_path in enumerate(local_torrents, 1):
    basename = os.path.basename(torrent_path)
    print(f"({i}/{p.total}) {basename}")

    try:
      new_tracker, new_torrent_filepath = generate_new_torrent_from_file(
        torrent_path,
        output_directory,
        red_api,
        ops_api,
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
    except TorrentAlreadyExistsError:
      p.already_exists.print("Found, but the output .torrent already exists.")
      continue
    except TorrentNotFoundError as e:
      p.not_found.print(str(e))
      continue
    except Exception as e:
      p.error.print(str(e))
      continue

  return p.report()
