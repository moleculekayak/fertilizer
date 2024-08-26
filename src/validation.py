import re
from urllib.parse import urlparse

from .filesystem import assert_path_exists


class ValidateConfigDict:
    def __init__(self, config_options):
        self.config_options = config_options
        self.validation_schema = {
            "red_key": r"^[a-z0-9.]{41}$",
            "ops_key": r"^[A-Za-z0-9+/]{116}$",
            "port": self.is_valid_port,
            "deluge_rpc_url": self.is_valid_url,
            "qbittorrent_url": self.is_valid_url,
            "inject_torrents": self.is_boolean,
            "injection_link_directory": assert_path_exists,
        }
        print(self.config_options)

    def validate(self):
        validated_values = {}
        validation_errors = {}

        for key, validator in self.validation_schema.items():
            value = self.config_options.get(key, None)
            if value is not None:
                try:
                    if callable(validator):
                        validated_values[key] = (
                            validator(value)
                            if "url" not in key
                            else validator(key, value)
                        )
                    else:
                        if re.fullmatch(validator, value):
                            validated_values[key] = value
                        else:
                            validation_errors[key] = (
                                f"Value does appear to match known API key patterns {key}: {value}"
                            )
                except Exception as e:
                    validation_errors[key] = str(e)
            else:
                if ("url" in key and self.should_set_rpc_url()
                    and (not self.config_options.get("deluge_rpc_url", None)
                         and not self.config_options.get("qbittorrent_url", None))) or "_key" in key:
                    validation_errors[key] = f"Missing required key: {key}"
        if validation_errors:
            raise ValueError(f"Validation errors: {validation_errors}")
        return validated_values

    @staticmethod
    def is_valid_url(key, value):
        parsed_url = urlparse(value)
        if parsed_url.scheme and parsed_url.netloc:
            if not parsed_url.password:
                if "deluge" in key:
                    raise Exception(
                        "You need to define a password in the Deluge RPC URL. (e.g. http://:<PASSWORD>@localhost:8112/json)"
                    )

            return parsed_url  # return the parsed URL
        raise ValueError(f"Invalid URL provided: {value}")

    @staticmethod
    def is_boolean(value):
        if isinstance(value, str):
            return True if value.lower().strip() == "true" else False
        raise ValueError(f"{value} is not a boolean")

    def should_set_rpc_url(self):
        inject_is_true = (
            True
            if self.config_options.get("inject_torrents", False).lower() == "true"
            else False
        )
        if inject_is_true:
            return True

    @staticmethod
    def is_valid_port(value):
        if value.isdigit() and 1 <= int(value) <= 65535:
            return int(value)  # Return the port number as an integer
        raise ValueError(f"Invalid Port ({value}): Not between 1 and 65535")
