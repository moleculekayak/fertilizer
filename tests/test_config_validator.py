import pytest
# from unittest import mock

from .helpers import SetupTeardown

from fertilizer.config_validator import ConfigValidator


@pytest.fixture
def red_key():
  return "a" * 41


@pytest.fixture
def ops_key():
  return "b" * 116


@pytest.fixture
def valid_config(red_key, ops_key):
  return {
    "red_key": red_key,
    "ops_key": ops_key,
    "port": "1234",
    "deluge_rpc_url": "http://:pass@deluge:8112",
    "inject_torrents": "true",
    "injection_link_directory": "/tmp/injection",
  }


class TestValidate(SetupTeardown):
  def test_returns_when_basic_config_is_valid(self, red_key, ops_key):
    config_dict = {
      "red_key": red_key,
      "ops_key": ops_key,
    }

    validator = ConfigValidator(config_dict)
    validated_config = validator.validate()

    assert validated_config == config_dict

  def test_returns_when_complex_config_valid(self, red_key, ops_key, valid_config):
    validator = ConfigValidator(valid_config)
    validated_config = validator.validate()

    assert validated_config == {
      "red_key": red_key,
      "ops_key": ops_key,
      "port": 1234,
      "deluge_rpc_url": "http://:pass@deluge:8112",
      "inject_torrents": True,
      "injection_link_directory": "/tmp/injection",
    }

  def test_raises_error_when_required_key_missing(self):
    config_dict = {
      "red_key": "",
      "ops_key": None,
    }

    validator = ConfigValidator(config_dict)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "red_key": Is required but was not found in the configuration' in str(excinfo.value)
    assert '- "ops_key": Is required but was not found in the configuration' in str(excinfo.value)

  def test_raises_error_if_injection_enabled_but_missing_injection_config(self, red_key, ops_key):
    config_dict = {"red_key": red_key, "ops_key": ops_key, "inject_torrents": "true"}

    validator = ConfigValidator(config_dict)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "torrent_clients": A torrent client URL is required if "inject_torrents" is enabled' in str(excinfo.value)
    assert (
      '- "injection_link_directory": An injection directory path is required if "inject_torrents" is enabled'
      in str(excinfo.value)
    )

  def test_raises_if_api_keys_present_but_invalid(self):
    config_dict = {
      "red_key": "a",
      "ops_key": "b",
    }

    validator = ConfigValidator(config_dict)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "red_key": does not appear to match known API key patterns: "a"' in str(excinfo.value)
    assert '- "ops_key": does not appear to match known API key patterns: "b"' in str(excinfo.value)

  def test_raises_if_port_isnt_valid(self, valid_config):
    valid_config["port"] = "not_a_number"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "port": Invalid "port" (not_a_number): Not between 1 and 65535' in str(excinfo.value)

  def test_raises_if_deluge_url_lacks_password(self, valid_config):
    valid_config["deluge_rpc_url"] = "http://deluge:8112"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert (
      '- "deluge_rpc_url": You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112/json)'
      in str(excinfo.value)
    )

  def test_raises_if_deluge_url_invalid(self, valid_config):
    valid_config["deluge_rpc_url"] = "not_a_url"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "deluge_rpc_url": Invalid "deluge_rpc_url" provided: not_a_url' in str(excinfo.value)

  def test_raises_if_qbit_url_invalid(self, valid_config):
    valid_config["qbittorrent_url"] = "not_a_url"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "qbittorrent_url": Invalid "qbittorrent_url" provided: not_a_url' in str(excinfo.value)

  def test_raises_if_torrent_injection_not_boolean(self, valid_config):
    valid_config["inject_torrents"] = "not_a_boolean"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "inject_torrents": value is not boolean ("true" or "false")' in str(excinfo.value)

  def test_raises_if_injection_directory_doesnt_exist(self, valid_config):
    valid_config["injection_link_directory"] = "/tmp/doesnt_exist"

    validator = ConfigValidator(valid_config)

    with pytest.raises(ValueError) as excinfo:
      validator.validate()

    assert '- "injection_link_directory": File or directory not found: /tmp/doesnt_exist' in str(excinfo.value)
