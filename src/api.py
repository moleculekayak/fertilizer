import json
from math import exp
from time import time, sleep

import requests

from .errors import AuthenticationError, handle_error


class GazelleAPI:
  """
  Methods for interacting with Gazelle-based trackers like RED and OPS.
  """

  def __init__(self, site_url, tracker_url, auth_header, rate_limit):
    self._s = requests.session()
    self._s.headers.update(auth_header)
    self._rate_limit = rate_limit
    self._timeout = 15
    self._last_used = 0

    self._max_retries = 20
    self._max_retry_time = 600
    self._retry_wait_time = lambda x: min(int(exp(x)), self._max_retry_time)

    self._announce_url = None
    self.sitename = self.__class__.__name__
    self.site_url = site_url
    self.tracker_url = tracker_url
    self.api_url = f"{self.site_url}/ajax.php"

  def get_account_info(self) -> dict:
    """
    Returns the account information of the user. Useful for fetching the passkey for the announce URL.
    """

    r = self.__get("index")
    if r["status"] != "success":
      raise AuthenticationError(r["error"])
    return r

  def find_torrent(self, torrent_hash: str) -> dict:
    return self.__get("torrent", hash=torrent_hash)

  @property
  def announce_url(self) -> str:
    if self._announce_url is None:
      self._announce_url = self.__get_announce_url()

    return self._announce_url

  def __get(self, action, **params):
    current_retries = 1

    while current_retries <= self._max_retries:
      now = time()
      if (now - self._last_used) > self._rate_limit:
        self._last_used = now
        params["action"] = action

        try:
          response = self._s.get(self.api_url, params=params, timeout=self._timeout)

          return json.loads(response.text)
        except requests.exceptions.Timeout as e:
          err = "Request timed out", e
        except requests.exceptions.ConnectionError as e:
          err = "Unable to connect", e
        except requests.exceptions.RequestException as e:
          err = "Request failed", f"{type(e).__name__}: {e}"
        except json.JSONDecodeError as e:
          err = "JSON decoding of response failed", e

        handle_error(
          description=err[0],
          exception_details=err[1],
          wait_time=self._retry_wait_time(current_retries),
          extra_description=f" (attempt {current_retries}/{self._max_retries})",
        )
        current_retries += 1
      else:
        sleep(0.2)

    handle_error(description="Maximum number of retries reached", should_raise=True)

  def __get_announce_url(self):
    try:
      account_info = self.get_account_info()
    except AuthenticationError as e:
      handle_error(description=f"Authentication to {self.sitename} failed", exception_details=str(e), should_raise=True)

    passkey = account_info["response"]["passkey"]
    return f"{self.tracker_url}/{passkey}/announce"


class OpsAPI(GazelleAPI):
  def __init__(self, api_key, delay_in_seconds=2):
    super().__init__(
      site_url="https://orpheus.network",
      tracker_url="https://home.opsfet.ch",
      auth_header={"Authorization": f"token {api_key}"},
      rate_limit=delay_in_seconds,
    )

    self.sitename = "OPS"


class RedAPI(GazelleAPI):
  def __init__(self, api_key, delay_in_seconds=2):
    super().__init__(
      site_url="https://redacted.sh",
      tracker_url="https://flacsfor.me",
      auth_header={"Authorization": api_key},
      rate_limit=delay_in_seconds,
    )

    self.sitename = "RED"
