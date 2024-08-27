import json
import os
import sys
import traceback

from colorama import Fore

from src.api import RedAPI, OpsAPI
from src.args import parse_args
from src.config import Config
from src.injection import Injection
from src.scanner import scan_torrent_directory, scan_torrent_file
from src.validation import ValidateConfigDict
from src.webserver import run_webserver


def cli_entrypoint(args):
  try:
    # using input_file means this is probably running as a script and extra printing wouldn't be appreciated
    should_print = args.input_directory or args.server
    config = Config()

    __build_configuration(config, args.config_file)
    validate = ValidateConfigDict(config.get_config())
    config.load_config([validate.validate()])
    command_log_wrapper(
      "Reading configuration:", should_print, lambda: config.get_config()
    )

    if config.inject_torrents:
      injector = command_log_wrapper("Connecting to torrent client:", should_print,
                                     lambda: Injection(config).setup())
    else:
      injector = None

    red_api, ops_api = command_log_wrapper("Verifying API keys:", should_print, lambda: __verify_api_keys(config))

    if args.server:
      run_webserver(args.input_directory, args.output_directory, red_api, ops_api, injector,
                    port=config.server_port)
    elif args.input_file:
      print(scan_torrent_file(args.input_file, args.output_directory, red_api, ops_api, injector))
    elif args.input_directory:
      print(scan_torrent_directory(args.input_directory, args.output_directory, red_api, ops_api, injector))
  except Exception as e:
    if args.verbose:
      print(traceback.format_exc())

    print(f"{Fore.RED}{str(e)}{Fore.RESET}")
    exit(1)


def __build_configuration(config: Config, config_file: str):
  file_config = {}
  if os.path.exists(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
      file_config = {key: str(value) for key, value in json.loads(f.read()).items() if value}

  env_vars = {
    key: value
    for key, value in {
      "inject_torrents": True if os.getenv("INJECT_TORRENTS", "").lower().strip() == "true" else False,
      "injection_link_directory": os.getenv("INJECTION_LINK_DIRECTORY"),
      "deluge_rpc_url": os.getenv("DELUGE_RPC_URL"),
      "qbittorrent_url": os.getenv("QBITTORRENT_URL"),
      "red_key": os.getenv("RED_KEY"),
      "ops_key": os.getenv("OPS_KEY"),
    }.items()
    if value
  }

  config.load_config([env_vars, file_config])


def __verify_api_keys(config):
  red_api = RedAPI(config.red_key)
  ops_api = OpsAPI(config.ops_key)

  # This will perform a lookup with the API and raise if there was a failure.
  # Also caches the announce URL for future use which is a nice bonus
  red_api.announce_url
  ops_api.announce_url

  return red_api, ops_api


def command_log_wrapper(label, should_print, func):
  def maybe_print(str, *args, **kwargs):
    if should_print:
      print(str, *args, **kwargs)
      sys.stdout.flush()

  maybe_print(f"{label} ", end="")

  try:
    result = func()
    maybe_print(f"{Fore.GREEN}Success{Fore.RESET}")
    return result
  except Exception as e:
    maybe_print(f"{Fore.RED}Error{Fore.RESET}")
    raise e


if __name__ == "__main__":
  args = parse_args()

  try:
    cli_entrypoint(args)
  except KeyboardInterrupt:
    print(f"{Fore.RED}Exiting...{Fore.RESET}")
    exit(1)
