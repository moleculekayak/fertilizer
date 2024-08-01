import sys
from time import sleep

from colorama import Fore


def handle_error(
  description: str,
  exception_details: (str | None) = None,
  wait_time: int = 0,
  extra_description: str = "",
  should_exit: bool = False,
) -> None:
  action = "Exiting" if should_exit else "Retrying"
  action += f" in {wait_time} seconds..." if wait_time else "..."
  exception_message = f"\n{Fore.LIGHTBLACK_EX}{exception_details}" if exception_details is not None else ""

  print(f"{Fore.RED}Error: {description}{extra_description}. {action}{exception_message}{Fore.RESET}")
  sleep(wait_time)

  if should_exit:
    sys.exit(1)


class AuthenticationError(Exception):
  pass


class TorrentDecodingError(Exception):
  pass


class UnknownTrackerError(Exception):
  pass


class TorrentNotFoundError(Exception):
  pass


class TorrentAlreadyExistsError(Exception):
  pass


class ConfigKeyError(Exception):
  pass


class TorrentClientError(Exception):
  pass


class TorrentInjectionError(Exception):
  pass
