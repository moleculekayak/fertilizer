import re
from urllib.parse import urlparse

from colorama import Fore

from .filesystem import assert_path_exists


class ValidateConfigDict:
  def __init__(self, config_options):
    self.config_options = config_options
    self.validation_schema = {
      "red_key": self.is_valid_red_key,
      "ops_key": self.is_valid_ops_key,
      "port": self.is_valid_port,
      "deluge_rpc_url": self.is_valid_deluge_url,
      "qbittorrent_url": self.is_valid_qbit_url,
      "inject_torrents": self.is_boolean,
      "injection_link_directory": assert_path_exists,
    }

  def validate(self):
    validation_errors = self.__validate_key_presence()
    validated_values = self.__validate_attributes(validation_errors)
    if validation_errors:
      print(f"Reading configuration: {Fore.RED}Error{Fore.RESET}\n")
      raise ValueError(f"Validation errors: {validation_errors}")
    return validated_values

  def __validate_key_presence(self):
    def is_tracker_keys_set():
      return sum(1 for key in self.config_options if "key" in key) == 2

    is_client_url_set = any('url' in key for key in self.config_options.keys())

    errors = {}
    if (self.should_set_torrent_client()) and not is_client_url_set:
      errors["torrent_clients"] = 'Required torrent client key missing with "inject_torrents" set True'

    if not (is_tracker_keys_set()):
      missing_error = "Required tracker API key is missing"
      # missing_api_keys = { key: f'{missing_error} {key}' for key in ["red_key","ops_key"] if key not in self.config_options.keys()}
      missing_keys = [key for key in ["red_key", "ops_key"] if key not in self.config_options]
      for key in missing_keys:
        if key in missing_keys:
          errors[key] = f'{missing_error}'

    return errors

  def __validate_attributes(self, validation_errors):
    validated_values = {}
    for key, validator in self.validation_schema.items():
      value = self.config_options.get(key, None)
      if value is not None:
        try:
          validated_values[key] = validator(str(value))
        except Exception as e:
          validation_errors[key] = str(e)
    return validation_errors or validated_values

  def should_set_torrent_client(self):
    return str(self.config_options.get("inject_torrents", False)).lower() == "true"

  @staticmethod
  def is_valid_qbit_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme and parsed_url.netloc:
      return parsed_url.geturl()  # return the parsed URL
    raise ValueError(f'Invalid "qbittorrent_url" provided: {url}')

  @staticmethod
  def is_valid_deluge_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme and parsed_url.netloc:
      if not parsed_url.password:
        raise Exception(
          "You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112/json)"
        )
      return parsed_url.geturl()  # return the parsed URL
    raise ValueError(f'Invalid "deluge_rpc_url" provided: {url}')

  @staticmethod
  def is_boolean(value):
    coerced = value.lower().strip()
    if coerced in ["true", "false"]:
      return coerced == "true"
    raise ValueError('"inject_torrents" value is not boolean ("True" or "False")')

  @staticmethod
  def is_valid_port(port):
    if port.isdigit() and 1 <= int(port) <= 65535:
      return int(port)  # Return the port number as an integer
    raise ValueError(f'Invalid "port" ({port}): Not between 1 and 65535')

  @staticmethod
  def is_valid_red_key(key):
    if re.fullmatch(r"^[a-z0-9.]{41}$", key):
      return key
    raise ValueError(f'"red_key" does appear to match known API key patterns: "{key}"')

  @staticmethod
  def is_valid_ops_key(key):
    if re.fullmatch(r"^[A-Za-z0-9+/]{116}$", key):
      return key
    raise ValueError(f'"ops_key" does appear to match known API key patterns: "{key}"')
