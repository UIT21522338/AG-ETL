import os
import requests
import json
from shared.logging.logger import get_logger
from urllib.parse import urlparse

logger = get_logger("copilot_client")

class CopilotClient:
    def __init__(self):
        self.api_url = self._normalize_api_url(os.getenv("LLM_API_URL"))
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o")

    @staticmethod
    def _normalize_api_url(raw_url: str) -> str:
        """
        Accept both full endpoint URL and provider base URL.
        Examples:
          - https://api.deepseek.com                -> https://api.deepseek.com/chat/completions
          - https://api.deepseek.com/v1             -> https://api.deepseek.com/v1/chat/completions
          - https://api.deepseek.com/chat/completions (kept as-is)
        """
        if not raw_url:
            return ""

        url = raw_url.strip().rstrip("/")
        parsed = urlparse(url)
        path = (parsed.path or "").rstrip("/")

        if path.endswith("/chat/completions"):
            return url
        if path in ("", "/"):
            return f"{url}/chat/completions"
        if path.endswith("/v1"):
            return f"{url}/chat/completions"
        return url

    def chat(self, system_prompt: str, user_message: str) -> str:
        if not self.api_url:
            raise ValueError("LLM_API_URL is empty")
        if not self.api_key:
            raise ValueError("LLM_API_KEY is empty")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1
        }
        resp = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
