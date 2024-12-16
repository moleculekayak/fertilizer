from urllib.parse import urlparse, unquote

from fertilizer.utils import url_join


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
    host = f"{parsed_url.hostname}{(':' + str(parsed_url.port)) if parsed_url.port else ''}"
    origin = f"{parsed_url.scheme}://{host}"

    if base_path is not None:
      href = url_join(origin, base_path)
    else:
      href = url_join(origin, parsed_url.path)

    return href, username, password

  def _determine_label(self, torrent_info):
    current_label = torrent_info.get("label")

    if not current_label:
      return self.torrent_label

    if current_label == self.torrent_label or current_label.endswith(f".{self.torrent_label}"):
      return current_label

    return f"{current_label}.{self.torrent_label}"
