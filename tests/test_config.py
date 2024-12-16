from .helpers import SetupTeardown

from fertilizer.config import Config


class TestConfig(SetupTeardown):
  def test_loads_config(self):
    config = Config({"red_key": "red_key", "ops_key": "ops_key"})

    assert config.red_key == "red_key"
    assert config.ops_key == "ops_key"

  def test_returns_default_value_if_present(self):
    assert Config({}).server_port == "9713"


class TestBuildFromSources(SetupTeardown):
  def test_builds_from_config_file(self):
    config_dict = Config.build_config_dict("tests/support/config.json", {})

    assert config_dict["red_key"] == "red_key"
    assert config_dict["ops_key"] == "ops_key"

  def test_builds_from_env_vars(self):
    config_dict = Config.build_config_dict(
      "",
      {
        "RED_KEY": "red_key",
        "OPS_KEY": "ops_key",
        "PORT": "1234",
        "DELUGE_RPC_URL": "http://deluge:8112",
        "QBITTORRENT_URL": "http://qbittorrent:8080",
        "INJECT_TORRENTS": "true",
        "INJECTION_LINK_DIRECTORY": "/my/cool/dir",
      },
    )

    assert config_dict["red_key"] == "red_key"
    assert config_dict["ops_key"] == "ops_key"
    assert config_dict["port"] == "1234"
    assert config_dict["deluge_rpc_url"] == "http://deluge:8112"
    assert config_dict["qbittorrent_url"] == "http://qbittorrent:8080"
    assert config_dict["inject_torrents"]
    assert config_dict["injection_link_directory"] == "/my/cool/dir"

  def test_config_file_takes_precedence_over_env(self):
    config_dict = Config.build_config_dict("tests/support/config.json", {"RED_KEY": "env_red_key"})

    assert config_dict["red_key"] == "red_key"
