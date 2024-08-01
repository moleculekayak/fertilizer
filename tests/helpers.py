import os
import shutil


def get_support_file_path(name):
  return f"tests/support/files/{name}"


def get_torrent_path(name):
  return get_support_file_path(f"{name}.torrent")


def copy_and_mkdir(src, dst):
  os.makedirs(os.path.dirname(dst), exist_ok=True)
  shutil.copy(src, dst)
  return dst


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
    os.makedirs("/tmp/injection", exist_ok=True)

  def teardown_method(self):
    shutil.rmtree("/tmp/input", ignore_errors=True)
    shutil.rmtree("/tmp/output", ignore_errors=True)
    shutil.rmtree("/tmp/injection", ignore_errors=True)
    shutil.rmtree("/tmp/OPS", ignore_errors=True)
    shutil.rmtree("/tmp/RED", ignore_errors=True)
