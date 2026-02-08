import os
from typing import Any

from lib.DataBaze.databaze import DataBaze


DEFAULT_CONFIG = {
    "system": {
        "ignore_folders": [
            "__pycache__",
            "System Volume Information",
            "docs",
            "lib",
            "hosting_bot",
        ],
        "autorun": {
            ".": ["telegram_bot.py"],
        },
        "server_name": "",
    },
    "bot": {
        "token": "",
        "admins_chat_id": [],
    },
    "users": {},
    "link": {},
}


class ConfigStore:
    def __init__(self, root: str = ".") -> None:
        self.root = root
        self._db = DataBaze(root)
        self._config_file = self._db.file("config")

    def ensure(self) -> bool:
        created = self._config_file.create()
        if created:
            self._config_file.write(DEFAULT_CONFIG)
        return created

    def read(self) -> dict[str, Any]:
        return self._config_file.read() or {}

    def write(self, data: dict[str, Any]) -> None:
        self._config_file.write(data)

    def ensure_admins_are_users(self, root_dir: str) -> None:
        cfg = self.read()
        admins = cfg.get("bot", {}).get("admins_chat_id", [])
        users = cfg.setdefault("users", {})
        changed = False

        for admin_id in admins:
            admin_id = str(admin_id)
            if admin_id not in users:
                users[admin_id] = {"cmd": root_dir}
                changed = True

        if changed:
            self.write(cfg)

    @staticmethod
    def get_user_cwd(cfg: dict[str, Any], user_id: str, root_dir: str) -> str:
        return cfg.get("users", {}).get(user_id, {"cmd": root_dir}).get("cmd", root_dir)

    @staticmethod
    def set_user_cwd(cfg: dict[str, Any], user_id: str, cwd: str) -> None:
        users = cfg.setdefault("users", {})
        users.setdefault(user_id, {})["cmd"] = cwd
