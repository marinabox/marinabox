from pathlib import Path
import configparser
import boto3
import json

class AWSConfig:
    def __init__(self):
        self.config_path = Path.home() / '.marinabox' / 'config.ini'
        self.config = configparser.ConfigParser()
        
        if self.config_path.exists():
            self.config.read(self.config_path)
    
    @property
    def is_configured(self) -> bool:
        return 'aws' in self.config
    
    def get_session(self) -> boto3.Session:
        if not self.is_configured:
            raise ValueError("AWS is not configured. Run 'mb aws init' first.")
            
        return boto3.Session(
            aws_access_key_id=self.config['aws']['access_key'],
            aws_secret_access_key=self.config['aws']['secret_key'],
            region_name=self.config['aws']['region']
        )
    
    @property
    def bucket_name(self) -> str:
        if not self.is_configured:
            raise ValueError("AWS is not configured. Run 'mb aws init' first.")
        return f'marinabox-storage-{self.config["aws"]["access_key"].lower()[:8]}'
    
    @property
    def repository_name(self) -> str:
        return 'marinabox'

class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".marinabox"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

    def _load_config(self):
        if not self.config_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return {}
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def set_anthropic_key(self, key: str):
        self.config['anthropic_api_key'] = key
        self._save_config()

    def get_anthropic_key(self) -> str:
        return self.config.get('anthropic_api_key')