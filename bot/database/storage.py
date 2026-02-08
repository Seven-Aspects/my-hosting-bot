import os
from datetime import datetime
from typing import Any

from dbase import DataBase


class DataFile:
    def __init__(self, name: str, type: str = "json", encode: str = "utf-8", path: str = "data/", logs: bool = False):
        self.name = name
        self.type = type
        self.encode = encode
        self.path = path
        self.logs = logs

    def _full_path(self) -> str:
        return os.path.join(self.path, f"{self.name}.{self.type}")

    def create(self) -> bool:
        os.makedirs(self.path, exist_ok=True)
        file_path = self._full_path()
        is_created = not os.path.exists(file_path)
        DataBase(file_path=file_path, show_logs=False)
        return is_created

    def read(self) -> Any:
        file_path = self._full_path()
        if not os.path.exists(file_path):
            if self.logs:
                print(f"[DataFile - Read] Файл {file_path} не найден.")
            return None
        db = DataBase(file_path=file_path, show_logs=False)
        return db.get("data", None)

    def write(self, data: Any, rewrite: bool = True) -> None:
        file_path = self._full_path()
        if not os.path.exists(file_path):
            if self.logs:
                print(f"[DataFile - Write] Файл {file_path} не найден.")
            return

        db = DataBase(file_path=file_path, show_logs=False)
        if rewrite:
            db.update(data=data)
            return

        current = db.get("data", "")
        if self.type == "json":
            db.update(data=data)
        else:
            db.update(data=f"{current}{data}")

    def delete(self) -> None:
        file_path = self._full_path()
        if os.path.isfile(file_path):
            os.remove(file_path)

    def rename(self, new_name: str) -> None:
        old_path = self._full_path()
        new_path = os.path.join(self.path, f"{new_name}.{self.type}")
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            self.name = new_name

    def info(self) -> dict[str, Any] | None:
        file_path = self._full_path()
        if not os.path.exists(file_path):
            return None

        file_info = os.stat(file_path)
        return {
            "name": f"{self.name}.{self.type}",
            "path": file_path,
            "father": os.path.dirname(file_path),
            "size": file_info.st_size,
            "modified": datetime.fromtimestamp(file_info.st_mtime).strftime("%d.%m.%Y %H:%M:%S"),
        }


class DataBaze:
    def __init__(self, path: str = "data/", logs: bool = False):
        self.path = path
        self.logs = logs

    def file(self, name: str, type: str = "json", encode: str = "utf-8") -> DataFile:
        return DataFile(name, type, encode, self.path, self.logs)

    def delete(self) -> None:
        if not os.path.exists(self.path):
            return
        for item in os.listdir(self.path):
            item_path = os.path.join(self.path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
