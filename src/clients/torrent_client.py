from urllib.parse import urlparse, unquote


class TorrentClient:
  def __init__(self):
    self.torrent_label = "fertilizer"

  def _extract_credentials_from_url(self, url):
    parsed_url = urlparse(url)
    username = unquote(parsed_url.username) if parsed_url.username else ""
    password = unquote(parsed_url.password) if parsed_url.password else ""
    origin = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
    href = origin + (parsed_url.path if parsed_url.path != "/" else "")

    return href, username, password
