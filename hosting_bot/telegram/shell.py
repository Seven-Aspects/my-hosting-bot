import os
import platform
import subprocess
from typing import Any


def parse_folder(path: str) -> dict[str, list[str]]:
    result = {"folders": [], "files": []}
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path):
            result["folders"].append(item)
        else:
            result["files"].append(item)
    return result


def format_ls(server_name: str, mention: str, current_dir: str) -> str:
    data = parse_folder(current_dir)
    files_list = [f"📄 {item}" for item in data["files"]]
    dirs_list = [f"📁 {item}" for item in data["folders"]]
    return (
        f"{mention}@{server_name}:~{current_dir}$\n\n"
        + "<b>ᅠᅠПапки:</b>\n"
        + "\n".join(dirs_list)
        + "\n\n<b>ᅠᅠФайлы:</b>\n"
        + "\n".join(files_list)
    )


def execute(command: list[str], cwd: str) -> str:
    shell_flag = platform.system() == "Windows"
    command_to_run: Any = " ".join(command) if shell_flag else command

    try:
        result = subprocess.run(
            command_to_run,
            capture_output=True,
            text=True,
            cwd=cwd,
            shell=shell_flag,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return "⚠️ Превышено время выполнения команды"

    return result.stdout or result.stderr or "✅ Выполнено"
