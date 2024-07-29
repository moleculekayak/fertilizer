from colorama import Fore

from src.api import RedAPI, OpsAPI
from src.args import parse_args
from src.config import Config
from src.scanner import scan_torrent_directory

if __name__ == "__main__":
  args = parse_args()
  config = Config().load(args.config_file)

  # TODO: confirm that both trackers can be accessed before starting the scan
  red_api = RedAPI(config.red_key)
  ops_api = OpsAPI(config.ops_key)

  try:
    scan_torrent_directory(args.input_directory, args.output_directory, red_api, ops_api)
  except FileNotFoundError as e:
    print(f"{Fore.RED}{str(e)}{Fore.RESET}")
    exit(1)

