import logging
import os
import platform
import re
import shlex
import subprocess


PM2_CMD = "pm2.cmd" if platform.system() == "Windows" else "pm2"


class PM2Manager:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.process_ids: dict[str, str] = {}

    @staticmethod
    def parse_processes(pm2_output: str) -> list[list[str]]:
        processes: list[list[str]] = []
        cleaned = re.sub(r"\x1b\[[0-9;]*[mK]", "", pm2_output).strip()
        for line in cleaned.split("\n"):
            if "│" not in line:
                continue
            parts = [part.strip() for part in line.split("│") if part.strip()]
            if len(parts) >= 2 and parts[0].isdigit():
                processes.append([parts[0], f"{parts[1]}.py"])
        return processes

    def start_file(self, folder: str, command: str) -> None:
        parts = shlex.split(command)
        if not parts:
            return
        file_name = parts[0]
        full_path = os.path.join(folder, file_name)
        if not os.path.exists(full_path):
            self.logger.error("[pm2] file not found: %s", full_path)
            return

        pm2_command = [PM2_CMD, "start", full_path]
        if len(parts) > 1:
            pm2_command.extend(["--interpreter", "python", "--"])
            pm2_command.extend(parts[1:])

        try:
            result = subprocess.run(
                pm2_command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=folder,
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error("[pm2] failed to start %s: %s", command, exc.stderr)
            return

        for process_id, process_name in self.parse_processes(result.stdout):
            if process_name == file_name:
                self.process_ids[command] = process_id
                self.logger.info("started %s with id=%s", command, process_id)
                return

    def start_from_autorun(self, root_dir: str, autorun: dict[str, list[str]], ignore_folders: list[str]) -> None:
        for rel_folder, files in autorun.items():
            folder = os.path.join(root_dir, rel_folder)
            if not os.path.isdir(folder):
                continue
            if rel_folder in ignore_folders:
                continue
            for command in files:
                self.start_file(folder, command)

    def stop_all(self) -> None:
        for command, process_id in list(self.process_ids.items()):
            try:
                subprocess.run(
                    [PM2_CMD, "stop", process_id],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    encoding="utf-8",
                )
                self.logger.info("stopped %s id=%s", command, process_id)
            except subprocess.CalledProcessError:
                self.logger.warning("unable to stop id=%s", process_id)
            del self.process_ids[command]
