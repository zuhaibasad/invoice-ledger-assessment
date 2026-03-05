from pydantic_settings import BaseSettings
from pathlib import Path
import yaml 

CONFIG_FILE_PATH = Path(__file__).parent.parent / 'config.yml'

def load_config(config_file_path):

    file = open(config_file_path, 'r')
    config = yaml.safe_load(file)
    file.close()
    return config

config = load_config(CONFIG_FILE_PATH)

class Settings(BaseSettings):
    """Immutable application settings, loaded once at startup."""
    
    app_name: str = "Invoice Ledger API"
    app_version: str = "1.0.0"
    duckdb_path: str = "../"+config['database']['path']
    debug: bool = False

    model_config = {"env_prefix": "LEDGER_"}


settings = Settings()
