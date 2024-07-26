import json
import os


class Config:
    def __init__(self):
        cwd = os.path.dirname(__file__)
        config_file = os.path.join(cwd, "settings.json")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"settings.json does not exist in '{cwd}'.")

        with open(config_file, "r", encoding="utf-8") as f:
            self._j = json.loads(f.read())

    @property
    def red_key(self):
        return self._j["RED"]

    @property
    def ops_key(self):
        return self._j["OPS"]
