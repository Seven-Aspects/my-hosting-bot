import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any


def parse_folder(path: str) -> dict[str, list[str]]:
    folders: list[str] = []
    files: list[str] = []
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_dir():
                folders.append(entry.name)
            else:
                files.append(entry.name)
    folders.sort()
    files.sort()
    return {"folders": folders, "files": files}


def build_tree(path: str, max_depth: int = 2, prefix: str = "") -> list[str]:
    if max_depth < 0:
        return []
    lines: list[str] = []
    content = parse_folder(path)
    items = [(name, True) for name in content["folders"]] + [(name, False) for name in content["files"]]
    for idx, (name, is_dir) in enumerate(items):
        branch = "└── " if idx == len(items) - 1 else "├── "
        icon = "📁" if is_dir else "📄"
        lines.append(f"{prefix}{branch}{icon} {name}")
        if is_dir and max_depth > 0:
            child_prefix = f"{prefix}{'    ' if idx == len(items) - 1 else '│   '}"
            lines.extend(build_tree(os.path.join(path, name), max_depth - 1, child_prefix))
    return lines


def format_ls(server_name: str, mention: str, current_dir: str) -> str:
    data = parse_folder(current_dir)
    files_list = [f"📄 {item}" for item in data["files"]] or ["—"]
    dirs_list = [f"📁 {item}" for item in data["folders"]] or ["—"]
    return (
        f"{mention}@{server_name}:~{current_dir}$\n\n"
        + "<b>Папки:</b>\n"
        + "\n".join(dirs_list)
        + "\n\n<b>Файлы:</b>\n"
        + "\n".join(files_list)
    )


def format_tree(server_name: str, mention: str, current_dir: str) -> str:
    lines = build_tree(current_dir, max_depth=2)
    body = "\n".join(lines[:200]) if lines else "(пусто)"
    return f"{mention}@{server_name}:~{current_dir}$ tree\n<pre>{body}</pre>"


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def format_pm2_output(output: str) -> str:
    clean = strip_ansi(output)
    if "│" not in clean:
        return clean
    lines = [line for line in clean.splitlines() if "│" in line]
    result: list[str] = []
    for line in lines:
        parts = [part.strip() for part in line.split("│")]
        if len(parts) < 10:
            continue
        row = [x for x in parts if x]
        if not row or not row[0].isdigit():
            continue
        result.append(f"• #{row[0]} {row[1]} | {row[8]} | up {row[6]} | cpu {row[9]} | mem {row[10]}")
    return "\n".join(result) if result else clean


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
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return "⚠️ Превышено время выполнения команды"

    out = (result.stdout or result.stderr or "").strip()
    if command and command[0].lower() == "pm2":
        return format_pm2_output(out or "✅ PM2 команда выполнена")
    if not out:
        return "✅ Команда выполнена без вывода"
    return out


def list_files_for_download(path: str) -> list[Path]:
    data = parse_folder(path)
    return [Path(path) / name for name in data["files"]]
