import os
import sys
import traceback

from colorama import Fore

from fertilizer.args import parse_args
from fertilizer.config import Config
from fertilizer.injection import Injection
from fertilizer.scanner import scan_torrent_directory, scan_torrent_file
from fertilizer.config_validator import ConfigValidator
from fertilizer.webserver import run_webserver


def cli_entrypoint(args):
  try:
    # using input_file means this is probably running as a script and extra printing wouldn't be appreciated
    should_print = args.input_directory or args.server
    config_dict = Config.build_config_dict(args.config_file, os.environ)
    validator = ConfigValidator(config_dict)
    config = command_log_wrapper("Reading configuration:", should_print, lambda: Config(validator.validate()))

    if config.inject_torrents:
      injector = command_log_wrapper("Connecting to torrent client:", should_print, lambda: Injection(config).setup())
    else:
      injector = None

    red_api, ops_api = command_log_wrapper(
      "Verifying API keys:", should_print, lambda: validator.verify_api_keys(config)
    )

    if args.server:
      run_webserver(args.input_directory, args.output_directory, red_api, ops_api, injector, port=config.server_port)
    elif args.input_file:
      print(scan_torrent_file(args.input_file, args.output_directory, red_api, ops_api, injector))
    elif args.input_directory:
      print(scan_torrent_directory(args.input_directory, args.output_directory, red_api, ops_api, injector))
  except Exception as e:
    if args.verbose:
      print(traceback.format_exc())

    print(f"{Fore.RED}{str(e)}{Fore.RESET}")
    exit(1)


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


def main():
  args = parse_args()

  try:
    cli_entrypoint(args)
  except KeyboardInterrupt:
    print(f"{Fore.RED}Exiting...{Fore.RESET}")
    exit(1)


if __name__ == "__main__":
  main()
