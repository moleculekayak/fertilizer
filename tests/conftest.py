import pytest
import requests_mock

from src.config import Config
from src.api import RedAPI, OpsAPI


@pytest.fixture
def mock_config():
  instance = Config()
  instance._json = {
    "red_key": "secret_red",
    "ops_key": "secret_ops",
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


# This _should_ prevent all tests from making real requests to the internet.
@pytest.fixture(autouse=True)
def stub_or_disable_requests():
  with requests_mock.Mocker():
    yield
