from math import exp
from time import time, sleep
import json

import requests

from errors import handle_error, AuthenticationError

class GazelleAPI:
    def __init__(self, site_url, tracker_url, auth_header, rate_limit):
        self._s = requests.session()
        self._s.headers.update(auth_header)
        self._rate_limit = rate_limit
        self._timeout = 15
        self._last_used = 0

        self._max_retries = 20
        self._max_retry_time = 600
        self._retry_wait_time = lambda x: min(int(exp(x)), self._max_retry_time)

        self.sitename = self.__class__.__name__
        self.site_url = site_url
        self.tracker_url = tracker_url
        self.api_url = f"{self.site_url}/ajax.php"
        self.announce_url = self._get_announce_url(tracker_url)

    def _get(self, action, **params):
        current_retries = 1

        while current_retries <= self._max_retries:
            now = time()
            if (now - self._last_used) > self._rate_limit:
                self._last_used = now
                params["action"] = action

                try:
                    r = self._s.get(self.api_url, params=params, timeout=self._timeout)
                    if action == "download":
                        return r
                    return json.loads(r.text)
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
                    extra_description=f" (attempt {current_retries}/{self._max_retries})"
                )
                current_retries += 1
            else:
                sleep(0.2)
        handle_error(
            description="Maximum number of retries reached",
            exit_=True
        )

    def _get_announce_url(self, tracker_url):
        try:
            account_info = self.get_account_info()
        except AuthenticationError as e:
            handle_error(
                description=f"Authentication to {self.sitename} failed",
                exception_details=e,
                exit_=True,
            )

        passkey = account_info["response"]["passkey"]
        return f"{tracker_url}/{passkey}/announce"

    def get_account_info(self):
        r = self._get("index")
        if r["status"] != "success":
            raise AuthenticationError(r["error"])
        return r

    def find_torrent(self, hash_):
        return self._get("torrent", hash=hash_)

    def download_torrent(self, torrent_id):
        return self._get("download", id=torrent_id)


class OPS(GazelleAPI):
  def __init__(self, api_key, delay_in_seconds=2):
    super().__init__(
      site_url="https://orpheus.network",
      tracker_url="https://home.opsfet.ch",
      auth_header={"Authorization": f"token {api_key}"},
      rate_limit=delay_in_seconds,
    )


class RED(GazelleAPI):
  def __init__(self, api_key, delay_in_seconds=1):
    super().__init__(
      site_url="https://redacted.ch",
      tracker_url="https://flacsfor.me",
      auth_header={"Authorization": api_key},
      rate_limit=delay_in_seconds,
    )
