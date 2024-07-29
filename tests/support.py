import os


def get_torrent_path(name):
  return f"tests/support/torrents/{name}.torrent"


class SetupTeardown:
  def setup_method(self):
    for f in os.listdir("/tmp"):
      if f.endswith(".torrent"):
        os.remove(os.path.join("/tmp", f))

  def teardown_method(self):
    pass
