from time import sleep

from colorama import Fore


def handle_error(
  description: str,
  exception_details: (str | None) = None,
  wait_time: int = 0,
  extra_description: str = "",
  should_raise: bool = False,
) -> None:
  action = "" if should_raise else "Retrying"
  action += f" in {wait_time} seconds..." if wait_time else ""
  exception_message = f"\n{Fore.LIGHTBLACK_EX}{exception_details}" if exception_details is not None else ""

  if should_raise:
    raise Exception(f"{description}{extra_description}. {action}{exception_message}{Fore.RESET}")
  else:
    print(f"{Fore.RED}Error: {description}{extra_description}. {action}{exception_message}{Fore.RESET}")
    sleep(wait_time)


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


class TorrentClientError(Exception):
  pass


class TorrentExistsInClientError(Exception):
  pass


class TorrentClientAuthenticationError(Exception):
  pass


class TorrentInjectionError(Exception):
  pass
