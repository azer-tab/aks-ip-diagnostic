import os

import yaml


class Config:
    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        self.config_data = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")

        with open(self.config_file) as file:
            return yaml.safe_load(file)

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def get_ip_exhaustion_threshold(self):
        return self.get("ip_exhaustion_threshold", 80)

    def get_subnet_capacity(self):
        return self.get("subnet_capacity", 100)

    def get_max_pods_limit(self):
        return self.get("max_pods_limit", 110)
