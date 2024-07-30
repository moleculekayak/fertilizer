from colorama import Fore

from src.api import RedAPI, OpsAPI
from src.args import parse_args
from src.config import Config
from src.torrent import generate_new_torrent_from_file
from src.scanner import scan_torrent_directory


def cli_entrypoint():
  args = parse_args()
  config = Config().load(args.config_file)

  # TODO: confirm that both trackers can be accessed before starting the scan
  red_api = RedAPI(config.red_key)
  ops_api = OpsAPI(config.ops_key)

  try:
    if args.input_file:
      _, torrent_path = generate_new_torrent_from_file(args.input_file, args.output_directory, red_api, ops_api)
      print(torrent_path)
    elif args.input_directory:
      report = scan_torrent_directory(args.input_directory, args.output_directory, red_api, ops_api)
      print(report)
  except Exception as e:
    print(f"{Fore.RED}{str(e)}{Fore.RESET}")
    exit(1)


if __name__ == "__main__":
  try:
    cli_entrypoint()
  except KeyboardInterrupt:
    print(f"{Fore.RED}Exiting...{Fore.RESET}")
    exit(1)
