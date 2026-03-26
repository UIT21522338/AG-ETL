import os
import requests
from shared.logging.logger import get_logger

logger = get_logger("nifi_client")

class NiFiClient:
    def __init__(self, use_token_auth: bool = True):
        self.base_url = os.getenv("NIFI_BASE_URL", "").rstrip("/")
        self.username = os.getenv("NIFI_USERNAME")
        self.password = os.getenv("NIFI_PASSWORD")
        self.auth = (self.username, self.password)
        self.timeout = 30
        self.token = None
        self.use_token_auth = use_token_auth
        
    def get_token(self) -> str:
        """Get access token from NiFi /access/token endpoint"""
        if self.token:
            return self.token
            
        token_url = f"{self.base_url}/nifi-api/access/token"
        try:
            resp = requests.post(
                token_url,
                data={"username": self.username, "password": self.password},
                timeout=self.timeout,
                verify=False  # Ignore SSL for corporate environments
            )
            resp.raise_for_status()
            self.token = resp.text  # Token is returned as plain text
            logger.info(f"Successfully obtained NiFi token (length: {len(self.token)})")
            return self.token
        except Exception as e:
            logger.error(f"Failed to get NiFi token: {e}")
            raise

    def _get_headers(self) -> dict:
        """Get request headers with token or basic auth"""
        headers = {"Content-Type": "application/json"}
        if self.use_token_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_bulletins(self, limit: int = 100) -> list:
        url = f"{self.base_url}/nifi-api/flow/bulletin-board?limit={limit}"
        
        # Try token auth first if enabled
        if self.use_token_auth:
            try:
                if not self.token:
                    self.get_token()
                headers = self._get_headers()
                resp = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                resp.raise_for_status()
                return resp.json().get("bulletinBoard", {}).get("bulletins", [])
            except Exception as e:
                logger.warning(f"Token auth failed: {e}, falling back to Basic Auth")
                self.token = None  # Reset token for fallback
        
        # Fallback to Basic Auth
        try:
            resp = requests.get(url, auth=self.auth, timeout=self.timeout, verify=False)
            resp.raise_for_status()
            return resp.json().get("bulletinBoard", {}).get("bulletins", [])
        except Exception as e:
            logger.error(f"Both token and basic auth failed: {e}")
            raise

    def get_processor_status(self, processor_id: str) -> dict:
        url = f"{self.base_url}/nifi-api/processors/{processor_id}"
        
        # Try token auth first if enabled
        if self.use_token_auth:
            try:
                if not self.token:
                    self.get_token()
                headers = self._get_headers()
                resp = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"Token auth failed: {e}, falling back to Basic Auth")
                self.token = None
        
        # Fallback to Basic Auth
        try:
            resp = requests.get(url, auth=self.auth, timeout=self.timeout, verify=False)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Both token and basic auth failed: {e}")
            raise
