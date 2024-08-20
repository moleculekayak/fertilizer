import os
import pytest
from unittest import mock

from .helpers import SetupTeardown

from src.config import Config
from src.errors import ConfigKeyError


class TestConfig(SetupTeardown):
  def test_loads_config(self):
    config = Config().load("tests/support/config.json")

    assert config.red_key == "red_key"
    assert config.ops_key == "ops_key"

  @mock.patch.dict(os.environ, {"RED_API_KEY": "red_key", "OPS_API_KEY": "ops_key"})
  def test_loads_via_env_var(self):
    config = Config().load("tests/support/badpath.json")

    assert config.red_key == "red_key"
    assert config.ops_key == "ops_key"

  def test_raises_error_on_missing_config_file(self):
    with pytest.raises(FileNotFoundError) as excinfo:
      Config().load("tests/support/missing.json")

    assert "tests/support/missing.json does not exist" in str(excinfo.value)

  def test_raises_error_on_missing_key_without_default(self):
    with open("/tmp/empty.json", "w") as f:
      f.write("{}")

    config = Config().load("/tmp/empty.json")

    with pytest.raises(ConfigKeyError) as excinfo:
      config.red_key

    assert "Key 'red_key' not found in config file." in str(excinfo.value)
    os.remove("/tmp/empty.json")

  def test_returns_default_value_if_present(self):
    with open("/tmp/empty.json", "w") as f:
      f.write("{}")

    config = Config().load("/tmp/empty.json")

    assert config.server_port == "9713"

    os.remove("/tmp/empty.json")
