import json
import os

from .errors import ConfigKeyError


class Config:
  """
  Class for loading and accessing the config file.
  """

  def __init__(self):
    self._json = {}

  def load(self, config_filepath: str):
    if os.getenv("RED_API_KEY") and os.getenv("OPS_API_KEY"):
      self._json = {"red_key": os.getenv("RED_API_KEY"), "ops_key": os.getenv("OPS_API_KEY")}
    elif os.path.exists(config_filepath):
      with open(config_filepath, "r", encoding="utf-8") as f:
        self._json = json.loads(f.read())
    else:
      raise FileNotFoundError(f"{config_filepath} does not exist and values not found in environment variables.")

    return self

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
  def deluge_rpc_url(self) -> str | None:
    return self.__get_key("deluge_rpc_url", must_exist=False) or None

  @property
  def qbittorrent_url(self) -> str | None:
    return self.__get_key("qbittorrent_url", must_exist=False) or None

  @property
  def inject_torrents(self) -> str | bool:
    return self.__get_key("inject_torrents", must_exist=False) or False

  @property
  def injection_link_directory(self) -> str | None:
    return self.__get_key("injection_link_directory", must_exist=False) or None

  def __get_key(self, key, must_exist=True):
    try:
      return self._json[key]
    except KeyError:
      if must_exist:
        raise ConfigKeyError(f"Key '{key}' not found in config file.")

      return None
