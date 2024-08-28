import sys
import traceback

from colorama import Fore

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

    config.build_config(args.config_file)
    validate = ValidateConfigDict(config.get_config())
    config.load_config([validate.validate()])
    command_log_wrapper("Reading configuration:", should_print, lambda: config.get_config())

    if config.inject_torrents:
      injector = command_log_wrapper("Connecting to torrent client:", should_print, lambda: Injection(config).setup())
    else:
      injector = None

    red_api, ops_api = command_log_wrapper(
      "Verifying API keys:", should_print, lambda: validate.verify_api_keys(config)
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


if __name__ == "__main__":
  args = parse_args()

  try:
    cli_entrypoint(args)
  except KeyboardInterrupt:
    print(f"{Fore.RED}Exiting...{Fore.RESET}")
    exit(1)
