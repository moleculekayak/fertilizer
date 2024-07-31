from colorama import Fore

from src.api import RedAPI, OpsAPI
from src.args import parse_args
from src.config import Config
from src.scanner import scan_torrent_directory, scan_torrent_file

from src.webserver import run_webserver

import os
from src.clients.deluge import Deluge


def cli_entrypoint(args):
  try:
    config = Config().load(args.config_file)
    red_api, ops_api = __verify_api_keys(config)

    if args.server:
      run_webserver(args.input_directory, args.output_directory, red_api, ops_api, port=config.server_port)
    elif args.input_file:
      print(scan_torrent_file(args.input_file, args.output_directory, red_api, ops_api))
    elif args.input_directory:
      print(scan_torrent_directory(args.input_directory, args.output_directory, red_api, ops_api))
  except Exception as e:
    print(f"{Fore.RED}{str(e)}{Fore.RESET}")
    exit(1)


def __verify_api_keys(config):
  red_api = RedAPI(config.red_key)
  ops_api = OpsAPI(config.ops_key)

  # This will perform a lookup with the API and raise if there was a failure.
  # Also caches the announce URL for future use which is a nice bonus
  red_api.announce_url
  ops_api.announce_url

  return red_api, ops_api


if __name__ == "__main__":
  deluge = Deluge(os.environ.get("DELUGE_RPC_URL"))
  deluge.setup()
  deluge.inject_torrent(os.environ.get("TORRENT_HASH"), 'foo.torrent')

  # print(res)
  # args = parse_args()

  # try:
  #   cli_entrypoint(args)
  # except KeyboardInterrupt:
  #   print(f"{Fore.RED}Exiting...{Fore.RESET}")
  #   exit(1)
