import os
from urllib.parse import urlparse, unquote

from src.filesystem import sane_join


class TorrentClient:
  def __init__(self):
    self.torrent_label = "fertilizer"

  def setup(self):
    raise NotImplementedError

  def get_torrent_info(self, *_args, **_kwargs):
    raise NotImplementedError

  def inject_torrent(self, *_args, **_kwargs):
    raise NotImplementedError

  def _extract_credentials_from_url(self, url, base_path=None):
    parsed_url = urlparse(url)
    username = unquote(parsed_url.username) if parsed_url.username else ""
    password = unquote(parsed_url.password) if parsed_url.password else ""
    origin = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"

    if base_path is not None:
      href = sane_join(origin, os.path.normpath(base_path))
    else:
      href = sane_join(origin, (parsed_url.path if parsed_url.path != "/" else ""))

    return href, username, password
