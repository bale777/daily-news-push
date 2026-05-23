import time
from abc import ABC, abstractmethod

import requests

from news_pusher.config import Config


class PushProvider(ABC):
    @abstractmethod
    def send(self, title: str, content: str) -> bool:
        """Return True on success."""


class ServerChanProvider(PushProvider):
    def __init__(self, sendkey: str, api_url: str = "https://sctapi.ftqq.com"):
        self.sendkey = sendkey
        self.api_url = api_url

    def send(self, title: str, content: str) -> bool:
        url = f"{self.api_url}/{self.sendkey}.send"
        try:
            resp = requests.post(
                url,
                data={"title": title, "desp": content},
                timeout=30,
            )
            data = resp.json()
            return data.get("code") == 0
        except Exception:
            return False


class PushPlusProvider(PushProvider):
    def __init__(self, token: str, api_url: str = "http://www.pushplus.plus/send"):
        self.token = token
        self.api_url = api_url

    def send(self, title: str, content: str) -> bool:
        try:
            resp = requests.post(
                self.api_url,
                json={
                    "token": self.token,
                    "title": title,
                    "content": content,
                    "template": "markdown",
                },
                timeout=30,
            )
            data = resp.json()
            return data.get("code") == 200
        except Exception:
            return False


class PushService:
    def __init__(self, config: Config):
        self.config = config
        self.providers: list[PushProvider] = []

        push = config.push
        if push.provider in ("serverchan", "both"):
            if push.serverchan_sendkey and "your_" not in push.serverchan_sendkey:
                self.providers.append(
                    ServerChanProvider(push.serverchan_sendkey, push.serverchan_api_url)
                )
        if push.provider in ("pushplus", "both"):
            if push.pushplus_token and "your_" not in push.pushplus_token:
                self.providers.append(
                    PushPlusProvider(push.pushplus_token, push.pushplus_api_url)
                )

    def send(self, title: str, content: str) -> bool:
        if not self.providers:
            return False

        success = False
        for provider in self.providers:
            for attempt in range(1, 4):
                if provider.send(title, content):
                    success = True
                    break
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
        return success
