import re
from urllib.parse import urlparse

from .api import RedAPI, OpsAPI
from .filesystem import assert_path_exists


class ConfigValidator:
  REQUIRED_KEYS = ["red_key", "ops_key"]
  TORRENT_CLIENT_KEYS = ["deluge_rpc_url", "transmission_rpc_url", "qbittorrent_url"]

  def __init__(self, config_dict):
    self.config_dict = config_dict
    self.validation_schema = {
      "red_key": self.__is_valid_red_key,
      "ops_key": self.__is_valid_ops_key,
      "port": self.__is_valid_port,
      "deluge_rpc_url": self.__is_valid_deluge_url,
      "transmission_rpc_url": self.__is_valid_transmission_rpc_url,
      "qbittorrent_url": self.__is_valid_qbit_url,
      "inject_torrents": self.__is_boolean,
      "injection_link_directory": assert_path_exists,
    }

  @staticmethod
  def verify_api_keys(config):
    red_api = RedAPI(config.red_key)
    ops_api = OpsAPI(config.ops_key)

    # This will perform a lookup with the API and raise if there was a failure.
    # Also caches the announce URL for future use which is a nice bonus
    red_api.announce_url
    ops_api.announce_url

    return red_api, ops_api

  def validate(self):
    presence_errors = self.__validate_key_presence()
    validation_errors, validated_values = self.__validate_attributes(presence_errors)

    if validation_errors:
      raise ValueError(self.__format_validation_errors(validation_errors))
    return validated_values

  def __validate_key_presence(self):
    errors = {}

    for key in self.REQUIRED_KEYS:
      if not self.config_dict.get(key):
        errors[key] = "Is required but was not found in the configuration"

    if self.__torrent_injection_enabled():
      if not any(self.config_dict.get(key) for key in self.TORRENT_CLIENT_KEYS):
        errors["torrent_clients"] = 'A torrent client URL is required if "inject_torrents" is enabled'

      if not self.config_dict.get("injection_link_directory"):
        errors["injection_link_directory"] = 'An injection directory path is required if "inject_torrents" is enabled'

    return errors

  def __validate_attributes(self, presence_errors):
    validated_values = {}
    validation_errors = presence_errors.copy()

    for key, validator in self.validation_schema.items():
      existing_error = presence_errors.get(key, None)
      value = self.config_dict.get(key, None)

      if existing_error is None and value is not None:
        try:
          validated_values[key] = validator(str(value))
        except Exception as e:
          validation_errors[key] = str(e)

    return validation_errors, validated_values

  def __format_validation_errors(self, errors):
    return "\n".join([f'- "{key}": {value}' for key, value in errors.items()])

  def __torrent_injection_enabled(self):
    return str(self.config_dict.get("inject_torrents", False)).lower() == "true"

  @staticmethod
  def __is_valid_qbit_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme and parsed_url.netloc:
      return parsed_url.geturl()  # return the parsed URL
    raise ValueError(f'Invalid "qbittorrent_url" provided: {url}')

  @staticmethod
  def __is_valid_deluge_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme and parsed_url.netloc:
      if not parsed_url.password:
        raise Exception(
          "You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112/json)"
        )
      return parsed_url.geturl()  # return the parsed URL
    raise ValueError(f'Invalid "deluge_rpc_url" provided: {url}')

  @staticmethod
  def __is_valid_transmission_rpc_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme and parsed_url.netloc:
      if not parsed_url.password:
        raise Exception(
          "You need to define a password in the TransmissionBt RPC URL. (e.g. http://:<PASSWORD>@localhost:51413/transmission/rpc)"
        )
      return parsed_url.geturl()  # return the parsed URL
    raise ValueError(f'Invalid "transmission_rpc_url" provided: {url}')

  @staticmethod
  def __is_boolean(value):
    coerced = value.lower().strip()
    if coerced in ["true", "false"]:
      return coerced == "true"
    raise ValueError('value is not boolean ("true" or "false")')

  @staticmethod
  def __is_valid_port(port):
    if port.isdigit() and 1 <= int(port) <= 65535:
      return int(port)  # Return the port number as an integer
    raise ValueError(f'Invalid "port" ({port}): Not between 1 and 65535')

  @staticmethod
  def __is_valid_red_key(key):
    if re.fullmatch(r"^[a-z0-9.]{41}$", key):
      return key
    raise ValueError(f'does not appear to match known API key patterns: "{key}"')

  @staticmethod
  def __is_valid_ops_key(key):
    if re.fullmatch(r"^[A-Za-z0-9+/]{116}$", key):
      return key
    raise ValueError(f'does not appear to match known API key patterns: "{key}"')
