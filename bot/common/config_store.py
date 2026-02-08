import os
from typing import Any

from bot.database import DataBaze


DEFAULT_DATA = {
    "users": {},
    "link": {},
}


class ConfigStore:
    def __init__(self, root: str = ".") -> None:
        self.root = root
        storage_path = os.path.join(root, "data")
        self._db = DataBaze(storage_path)
        self._config_file = self._db.file("data")

    def ensure(self) -> bool:
        created = self._config_file.create()
        if created:
            self._config_file.write(DEFAULT_DATA)
        return created

    def read(self) -> dict[str, Any]:
        return self._config_file.read() or {"users": {}, "link": {}}

    def write(self, data: dict[str, Any]) -> None:
        self._config_file.write(data)

    def ensure_admins_are_users(self, root_dir: str, admins: list[str]) -> None:
        data = self.read()
        users = data.setdefault("users", {})
        changed = False
        for admin_id in admins:
            admin_id = str(admin_id)
            if admin_id not in users:
                users[admin_id] = {"cmd": root_dir}
                changed = True
        if changed:
            self.write(data)

    @staticmethod
    def get_user_cwd(data: dict[str, Any], user_id: str, root_dir: str) -> str:
        return data.get("users", {}).get(user_id, {"cmd": root_dir}).get("cmd", root_dir)

    @staticmethod
    def set_user_cwd(data: dict[str, Any], user_id: str, cwd: str) -> None:
        users = data.setdefault("users", {})
        users.setdefault(user_id, {})["cmd"] = cwd
