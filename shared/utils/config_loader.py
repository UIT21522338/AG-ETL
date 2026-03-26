import os
import yaml
from dotenv import load_dotenv

def load_env():
    load_dotenv()

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(os.path.expandvars(f.read()))
