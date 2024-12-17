import json
import os
from urllib.parse import ParseResult


class Config:
  """
  Class for working with configuration options
  """

  @classmethod
  def build_config_dict(cls, config_filepath: str, env_vars: dict):
    file_config = {}
    if os.path.exists(config_filepath):
      with open(config_filepath, "r", encoding="utf-8") as f:
        file_config = {key: str(value) for key, value in json.loads(f.read()).items() if value}

    formatted_env_vars = {
      key: value
      for key, value in {
        "red_key": env_vars.get("RED_KEY"),
        "ops_key": env_vars.get("OPS_KEY"),
        "port": env_vars.get("PORT"),
        "inject_torrents": True if env_vars.get("INJECT_TORRENTS", "").lower().strip() == "true" else False,
        "deluge_rpc_url": env_vars.get("DELUGE_RPC_URL"),
        "transmission_rpc_url": env_vars.get("TRANSMISSION_RPC_URL"),
        "qbittorrent_url": env_vars.get("QBITTORRENT_URL"),
        "injection_link_directory": env_vars.get("INJECTION_LINK_DIRECTORY"),
      }.items()
      if value
    }

    return {**formatted_env_vars, **file_config}

  def __init__(self, config: dict):
    self._config = config

  @property
  def red_key(self) -> str:
    return self._config["red_key"]

  @property
  def ops_key(self) -> str:
    return self._config["ops_key"]

  @property
  def server_port(self) -> str:
    return self._config.get("port", "9713")

  @property
  def deluge_rpc_url(self) -> ParseResult | None:
    return self._config.get("deluge_rpc_url")

  @property
  def transmission_rpc_url(self) -> ParseResult | None:
    return self._config.get("transmission_rpc_url")

  @property
  def qbittorrent_url(self) -> ParseResult | None:
    return self._config.get("qbittorrent_url")

  @property
  def inject_torrents(self) -> bool:
    return self._config.get("inject_torrents", False)

  @property
  def injection_link_directory(self) -> str | None:
    return self._config.get("injection_link_directory")
