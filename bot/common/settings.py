import os
from dataclasses import dataclass


DEFAULT_AUTORUN = {".": ["main.py telegram"]}
DEFAULT_IGNORE_FOLDERS = ["__pycache__", "System Volume Information", "docs", "data", "storage", "bot", ".git"]


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_admin_ids(value: str) -> list[str]:
    return [item for item in _parse_list(value)]


def _parse_autorun(value: str) -> dict[str, list[str]]:
    if not value.strip():
        return DEFAULT_AUTORUN
    items = _parse_list(value)
    commands: list[str] = []
    for item in items:
        if ":" in item:
            _, cmd = item.split(":", 1)
            if cmd.strip():
                commands.append(cmd.strip())
        else:
            commands.append(item)
    return {".": commands or DEFAULT_AUTORUN["."]}


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            row = line.strip()
            if not row or row.startswith("#") or "=" not in row:
                continue
            key, value = row.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admins_chat_id: list[str]
    server_name: str
    ignore_folders: list[str]
    autorun: dict[str, list[str]]



def load_settings() -> Settings:
    load_env_file()
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admins_chat_id=_parse_admin_ids(os.getenv("BOT_ADMINS_CHAT_ID", "")),
        server_name=os.getenv("BOT_SERVER_NAME", "Server"),
        ignore_folders=_parse_list(os.getenv("BOT_IGNORE_FOLDERS", ",".join(DEFAULT_IGNORE_FOLDERS)))
        or DEFAULT_IGNORE_FOLDERS,
        autorun=_parse_autorun(os.getenv("BOT_AUTORUN", ",".join(DEFAULT_AUTORUN["."]))),
    )
