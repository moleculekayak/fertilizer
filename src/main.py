from colorama import Fore

from api import RED, OPS
from args import get_args
from config import Config
from downloader import get_torrent_id, get_torrent_url, get_torrent_filepath, download_torrent
from filesystem import create_folder, get_files, get_filename
from parser import get_torrent_data, get_new_hash, get_source, save_torrent_data
from progress import Progress

def main():
  print("Hello!")

if __name__ == "__main__":
  # args = get_args()
  config = Config()

  # red = RED(config.red_key)
  # ops = OPS(config.ops_key)

  main()
