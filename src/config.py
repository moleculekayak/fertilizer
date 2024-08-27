import json
import os
from urllib.parse import ParseResult

from .errors import ConfigKeyError


class Config:
  """
  Class for loading and accessing the config file.
  """

  def __init__(self):
    self._config = {}

  def load_config(self, configs: list[dict[str, str | bool | ParseResult]]):
    for config in configs:
      self._config |= config
    if not self._config:
      raise FileNotFoundError("Configuration not found.")

  def get_config(self):
    return self._config

  def build_config(self, config_file: str):
    file_config = {}
    if os.path.exists(config_file):
      with open(config_file, "r", encoding="utf-8") as f:
        file_config = {key: str(value) for key, value in json.loads(f.read()).items() if value}

    env_vars = {
      key: value
      for key, value in {
        "inject_torrents": True if os.getenv("INJECT_TORRENTS", "").lower().strip() == "true" else False,
        "injection_link_directory": os.getenv("INJECTION_LINK_DIRECTORY"),
        "deluge_rpc_url": os.getenv("DELUGE_RPC_URL"),
        "qbittorrent_url": os.getenv("QBITTORRENT_URL"),
        "red_key": os.getenv("RED_KEY"),
        "ops_key": os.getenv("OPS_KEY"),
      }.items()
      if value
    }

    self.load_config([env_vars, file_config])

  @property
  def red_key(self) -> str:
    return self.__get_key("red_key")

  @property
  def ops_key(self) -> str:
    return self.__get_key("ops_key")

  @property
  def server_port(self) -> str:
    return self.__get_key("port", must_exist=False) or "9713"

  @property
  def deluge_rpc_url(self) -> ParseResult | None:
    return self.__get_key("deluge_rpc_url", must_exist=False) or None

  @property
  def qbittorrent_url(self) -> ParseResult | None:
    return self.__get_key("qbittorrent_url", must_exist=False) or None

  @property
  def inject_torrents(self) -> str | bool:
    return self.__get_key("inject_torrents", must_exist=False) or False

  @property
  def injection_link_directory(self) -> str | None:
    return self.__get_key("injection_link_directory", must_exist=False) or None

  def __get_key(self, key, must_exist=True):
    try:
      return self._config[key]
    except KeyError:
      if must_exist:
        raise ConfigKeyError(f"Key '{key}' not found in config file.")

      return None
