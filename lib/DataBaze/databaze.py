import os, json, shutil
from datetime import datetime
        
class DataFile:

    """
        DataFile(name, type, encode, path, logs)

        name - Название файла
        type - Расширение файла (default - json)
        encode - Кодировка файла (default - utf-8)
        path - Путь до файла (default - .)
        logs - Показывать/Скрывать логи (default - False)

        .create() - создает файл и, при необходимости, создает папку
        .read() - чтение файла (если файл - json, то автоматическое переобразование в словарь)
        .write(data) - запись данных в файл (если файл - json, то автоматическое переобразование в строчку)
        .delete() - удаление файла
        .rename(new_name) - переименование файла
        .info() - возвращает информацию о файле (родительская папка, путь, размер, название, дата последнего изменения)
    """

    def __init__(self, name: str, type: str = "json", encode: str = "utf-8", path: str = ".", logs: bool = False):

        """
            name - Название файла
            type - Расширение файла (default - json)
            encode - Кодировка файла (default - utf-8)
            path - Путь до файла (default - .)
            logs - Показывать/Скрывать логи (default - False)
        """

        self.name = name
        self.type = type
        self.encode = encode
        self.path = path
        self.logs = logs

    def create(self):

        """
            .create() - создает файл и, при необходимости, создает папку
        """

        file_path = os.path.join(self.path, f'{self.name}.{self.type}')
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding=self.encode) as f:
                    f.write("")
                if self.logs: print(f'[DataFile - Create] {file_path} успешно создан.')
                return True
            except Exception as e:
                if self.logs: print(f'[DataFile - Create] Ошибка при создании файла {file_path}: {e}')
                return False
        else:
            if self.logs: print(f'[DataFile - Create] Файл уже существует: {file_path}')
            return "already"

    def read(self):

        """
            .read() - чтение файла (если файл - json, то автоматическое преобразование в словарь)
        """

        file_path = os.path.join(self.path, f'{self.name}.{self.type}')
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding=self.encode) as f:
                    if self.type == "json":
                        content = f.read()
                        if content.strip():
                            return json.loads(content)
                        else:
                            return {}
                    else:
                        return f.read()
                if self.logs: print(f'[DataFile - Read] Файл {file_path} успешно прочтен.')
            except json.JSONDecodeError as e:
                if self.logs: print(f'[DataFile - Read] Ошибка при чтении файла {file_path}: {e}')
            except Exception as e:
                if self.logs: print(f'[DataFile - Read] Неизвестная ошибка при чтении файла {file_path}: {e}')
        else:
            if self.logs: print(f'[DataFile - Read] Файл {file_path} не найден.')
            return None


    def write(self, data, rewrite: bool = True):

        """
            .write(data, type) - запись данных в файл (если файл - json, то автоматическое переобразование в строчку)
            data - Данные
            rewrite - Перезаписывать (True/False)
        """

        file_path = os.path.join(self.path, f'{self.name}.{self.type}')
        if os.path.exists(file_path):
            try:
                if not rewrite:
                    with open(file_path, "a", encoding=self.encode) as f:
                        if self.type == "json":
                            f.write(json.dumps(data, ensure_ascii=False, indent=4))
                            if self.logs: print(f'[DataFile - Write] Данные успешно записаны в файл {file_path}')
                        else:
                            f.write(str(data))
                            if self.logs: print(f'[DataFile - Write] Данные успешно записаны в файл {file_path}')
                else:
                    with open(file_path, "w", encoding=self.encode) as f:
                        if self.type == "json":
                            f.write(json.dumps(data, ensure_ascii=False, indent=4))
                            if self.logs: print(f'[DataFile - Write] Данные успешно записаны в файл {file_path}')
                        else:
                            f.write(str(data))
                            if self.logs: print(f'[DataFile - Write] Данные успешно записаны в файл {file_path}')
            except TypeError as e:
                if self.logs: print(f'[DataFile - Write] Ошибка при записи в файл {file_path}: {e}')
            except Exception as e:
                if self.logs: print(f'[DataFile - Write] Неизвестная ошибка при записи в файл {file_path}: {e}')
        else:
            if self.logs: print(f'[DataFile - Write] Файл {file_path} не найден.')

    def delete(self):

        """
            .delete() - удаление файла
        """
        
        file_path = os.path.join(self.path, f'{self.name}.{self.type}') if self.type != "" else ""
        if os.path.exists(file_path):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    if self.logs: print(f"[DataFile - Delete] Файл {file_path} успешно удален.")
            except Exception as e:
                if self.logs: print(f"[DataFile - Delete] Ошибка при удалении файла {file_path}: {e}")
        else:
            if self.logs: print(f'[DataFile - Delete] Файл {file_path} не найден.')

    def rename(self, new_name: str):

        """
            .rename(new_name) - переименование файла
        """

        old_file_path = os.path.join(self.path, f'{self.name}.{self.type}')
        new_file_path = os.path.join(self.path, f'{new_name}.{self.type}')
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)
            if self.logs: print(f"[DataFile - Rename] Файл {self.name} успешно переименнован в {new_name}")
            self.name = new_name
        else:
            if self.logs: print(f'[DataFile - Rename] Файл {old_file_path} не найден.')

    def info(self):

        """
            .info() - возвращает информацию о файле (родительская папка, путь, размер, название, дата последнего изменения)
        """

        file_path = os.path.join(self.path, f'{self.name}.{self.type}')
        if os.path.exists(file_path):
            file_info = os.stat(file_path)
            parent_folder = os.path.dirname(file_path)
            file_size = file_info.st_size
            last_modified = file_info.st_mtime
            last_modified_formatted = datetime.fromtimestamp(last_modified).strftime('%d.%m.%Y %H:%M:%S')
            info = {
                "name": f'{self.name}.{self.type}',
                "path": file_path,
                "father": parent_folder,
                "size": file_size,
                "modified": last_modified_formatted,
            }
            if self.logs: print(f"[DataFile - Info] Информация о файле {file_path} успешно получена.")
            return info
        else:
            if self.logs: print(f'[DataFile - Info] Файл {file_path} не найден.')
            return None


class DataBaze:

    """
        DataBaze(path, logs)

        path - путь до папки
        logs - Показывать/Скрывать логи (default - False)

        .file(name, type, encode) - обьявляет файл
        .delete() - удаляет все файлы в базе данных
    """
        
    def __init__(self, path: str = "data/", logs: bool = False):

        """
            path - путь до папки
            logs - Показывать/Скрывать логи (default - False)
        """
        
        self.path = path
        self.logs = logs

    def file(self, name: str, type: str = "json", encode: str = "utf-8"):

        """
            .file(name, type, encode) - обьявляет файл
        """

        return DataFile(name, type, encode, self.path, self.logs)

    def delete(self):

        """
            .delete() - удаляет все файлы в папке
        """
        
        if os.path.exists(self.path):
            try:
                shutil.rmtree(self.path)
                if self.logs:
                    print(f"[DataFile - Delete] Папка {self.path} успешно удалена.")
            except Exception as e:
                if self.logs:
                    print(f"[DataFile - Delete] Ошибка при удалении папки {self.path}: {e}")
        else:
            if self.logs:
                print(f'[DataFile - Delete] Папка {self.path} не найдена.')