import os
import hvac
from dotenv import load_dotenv

load_dotenv()

class SecretManager:
    def __init__(self):
        self.vault_url = os.getenv("VAULT_URL")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.client = None
        
        if self.vault_url and self.vault_token:
            try:
                self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
                if not self.client.is_authenticated():
                    print("Warning: Vault authentication failed.")
                    self.client = None
            except Exception as e:
                print(f"Warning: Could not connect to Vault: {e}")
                self.client = None

    def get_secret(self, key, default=None):
        """
        Tries to get secret from Vault, falls back to environment variables.
        """
        if self.client:
            try:
                # Assuming secrets are stored in 'secret/data/kyb_agent'
                read_response = self.client.secrets.kv.v2.read_secret_version(path='kyb_agent')
                secrets = read_response['data']['data']
                if key in secrets:
                    return secrets[key]
            except Exception as e:
                print(f"Error reading from Vault: {e}")

        # Fallback to environment variables
        return os.getenv(key, default)

# Singleton instance
secrets_manager = SecretManager()
