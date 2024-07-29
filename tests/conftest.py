import pytest

from src.config import Config
from src.api import RedAPI, OpsAPI


@pytest.fixture
def mock_config():
  instance = Config()
  instance._json = {
    "RED": "secret_red",
    "OPS": "secret_ops",
  }
  return instance


@pytest.fixture
def red_api():
  instance = RedAPI("redsecret", delay_in_seconds=0)
  instance._max_retries = 1
  return instance


@pytest.fixture
def ops_api():
  instance = OpsAPI("opssecret", delay_in_seconds=0)
  instance._max_retries = 1
  return instance
