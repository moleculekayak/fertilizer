from urllib.parse import urlparse, urljoin


class TorrentClient:
  def __init__(self):
    self.torrent_label = "fertilizer"

  def setup(self):
    raise NotImplementedError

  def get_torrent_info(self, *_args, **_kwargs):
    raise NotImplementedError

  def inject_torrent(self, *_args, **_kwargs):
    raise NotImplementedError

  @staticmethod
  def _extract_credentials_from_url(url, base_path=None):
    url = urlparse(url)
    username = url.username if url.username else ""
    password = url.password if url.password else ""
    origin = f"{url.scheme}://{url.hostname}{f":{url.port}" if url.port else ""}"
    if base_path is not None:
      href = urljoin(origin, base_path)
    else:
      href = urljoin(origin, (url.path if url.path != "/" else ""))
    print(href)
    return url.geturl() if base_path is None else href, username, password

  def _determine_label(self, torrent_info):
    current_label = torrent_info.get("label")

    if not current_label:
      return self.torrent_label

    if current_label == self.torrent_label or current_label.endswith(f".{self.torrent_label}"):
      return current_label

    return f"{current_label}.{self.torrent_label}"
