import os
import shutil


def get_torrent_path(name):
  return f"tests/support/torrents/{name}.torrent"


def copy_and_mkdir(src, dst):
  os.makedirs(os.path.dirname(dst), exist_ok=True)
  return shutil.copy(src, dst)


class SetupTeardown:
  TORRENT_SUCCESS_RESPONSE = {"status": "success", "response": {"torrent": {"filePath": "foo", "id": 123}}}
  TORRENT_KNOWN_BAD_RESPONSE = {"status": "failure", "error": "bad hash parameter"}
  TORRENT_UNKNOWN_BAD_RESPONSE = {"status": "failure", "error": "unknown error"}
  ANNOUNCE_SUCCESS_RESPONSE = {"status": "success", "response": {"passkey": "bar"}}

  def setup_method(self):
    for f in os.listdir("/tmp"):
      if f.endswith(".torrent"):
        os.remove(os.path.join("/tmp", f))

    os.makedirs("/tmp/input", exist_ok=True)
    os.makedirs("/tmp/output", exist_ok=True)

  def teardown_method(self):
    shutil.rmtree("/tmp/input", ignore_errors=True)
    shutil.rmtree("/tmp/output", ignore_errors=True)
    shutil.rmtree("/tmp/OPS", ignore_errors=True)
    shutil.rmtree("/tmp/RED", ignore_errors=True)
