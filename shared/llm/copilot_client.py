import os
import requests
import json
from shared.logging.logger import get_logger

logger = get_logger("copilot_client")

class CopilotClient:
    def __init__(self):
        self.api_url = os.getenv("LLM_API_URL")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o")

    def chat(self, system_prompt: str, user_message: str) -> str:
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
