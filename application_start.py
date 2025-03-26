# Modules
import os
import time
import platform
import subprocess
import socket
import json
import re
import logging


from lib.DataBaze.databaze import (
    DataBaze
)


# Настройка логгера
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


logger = logging.getLogger(__name__)


# Настройка базы данных
db = DataBaze('.')
config = db.file('config')


# Проверка и создание конфига
if config.create() == True:
    config.write('''{
    "system": {
        "ignore_folders": [
            "__pycache__",
            "System Volume Information",
            "home",
            "docs",
            "examples",
            "lib"
        ],
        "autorun": {
            ".": [
                "telegram_bot.py
            ]
        },
        "server_name": ""
    },
    "bot": {
        "token": "",
        "admins_chat_id": []
    },
    "users": {},
    "link": {}
}''')
    

    print('Заполните данные в файле config.json')


    quit()


# Работа с конфигом
def get_config() -> dict:
    return config.read()


def update_config(new_config: dict) -> None:
    config.write(new_config)


# Получение игнорируемых папок
def get_ignore_folders() -> list:
    ignore_folders = get_config().get('system', {}).get('ignore_folders', [])


    if ignore_folders != []:
        return ignore_folders
    

    return []


# Константы
CHECK_INTERVAL = 180
PROCESS_IDS = {}
IGNORE_FOLDERS = get_ignore_folders()
PM2_CMD = "pm2.cmd" if platform.system() == "Windows" else "pm2"


# Проверка соединения с интернетом
def check_internet() -> bool:
    """Проверяет наличие интернет-соединения с помощью комбинации методов."""
    result = 0


    # Проверка подключения через сокет к DNS-серверам
    hosts = [
        ('8.8.8.8', 53),  # Google DNS
        ('1.1.1.1', 53),  # Cloudflare DNS
    ]


    for host, port in hosts:
        try:
            socket.create_connection((host, port), timeout=5)


            result += 1


        except (OSError, socket.timeout):
            continue


        except:
            continue


    # Проверка через ping нескольких хостов
    ping_hosts = ['8.8.8.8', '1.1.1.1']
    param = '-n' if platform.system().lower() == 'windows' else '-c'


    for host in ping_hosts:
        try:
            kwargs = {
                'args': ['ping', param, '1', host],
                'timeout': 5,
                'stderr': subprocess.STDOUT,
            }


            if platform.system() == 'Windows':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW


            subprocess.check_output(**kwargs)


            result += 1


        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue


        except:
            continue


    return True if result >= 2 else False


# Обработка ответа от PM2
def handle_pm2_output(output: str) -> str:
    processes = []


    for line in output.split('\n'):
        if '│' in line:
            parts = [p.strip() for p in line.split('│') if p.strip()]


            if len(parts) >= 6 and parts[0].isdigit():
                processes.append([parts[0], parts[1]+'.py'])


    return processes


def parse_autorun(folder: str, files: list) -> list:
    processes = []


    try:
        for file in files:
            file_name = file
            full_path = os.path.join(folder, file_name)


            if not os.path.exists(full_path):
                logger.error(f'[parse_autorun()] Файл {full_path} не найден')
                

                continue


            try:
                result = subprocess.run(
                    [PM2_CMD, "start", full_path],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    cwd=folder
                )
            
                processes = handle_pm2_output(re.sub(r'\x1b\[[0-9;]*[mK]', '', result.stdout).strip())

                
                for proc in processes:
                    if proc[1] == file_name:
                        PROCESS_IDS[proc[1]] = str(proc[0])


                        logger.info(f"Успешно запущен процесс: {file_name} (ID: {proc[0]})")


                        break


            except subprocess.CalledProcessError as e:
                logger.error(f"[parse_autorun()] Ошибка запуска {file_name}: {e.stderr}")


            except json.JSONDecodeError:
                logger.error("[parse_autorun()]  Ошибка парсинга вывода PM2")


    except Exception as e:
        logger.error(f"[parse_autorun()] Ошибка обработки файлов папки: {str(e)}")


    return processes


def terminate_process(process_id: str) -> None:
    """Остановка процесса с проверкой ID"""
    if process_id is None:
        logger.error("[terminate_process()] Неверный ID процесса")


        return

    try:
        subprocess.run(
            [PM2_CMD, "stop", str(process_id)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            encoding='utf-8'
        )


        logger.info(f"Процесс {process_id} остановлен")


    except subprocess.CalledProcessError as e:
        logger.error(f"[terminate_process()] Ошибка остановки {process_id}: {e.stderr}")


def stop_all() -> None:
    """Остановка всех процессов с очисткой словаря"""
    for name, pid in list(PROCESS_IDS.items()):
        terminate_process(str(pid))


        del PROCESS_IDS[name]


def start_all() -> None:
    """Запуск процессов с обработкой кодировки"""
    logger.info('Запуск процессов')


    for item in get_config().get('system', {}).get('autorun', {}):
        folder = os.path.join(os.getcwd(), item)


        if os.path.isdir(folder) and folder.replace(os.getcwd()+'\\', '') not in IGNORE_FOLDERS \
            and get_config().get('system', {}).get('autorun', {}).get(item, []) != []:
            parse_autorun(folder, get_config().get('system', {}).get('autorun', {}).get(item, []))


def main():
    """Улучшенный цикл с устойчивой обработкой состояния"""
    connection_lost = False
    fail_counter = 0

    try:
        logger.info("Инициализация системы...")


        start_all()


        process_status = True

        
        while True:
            try:
                if check_internet():
                    if connection_lost:
                        logger.info("Соединение восстановлено! Перезапуск сервисов...")


                        start_all()


                        process_status = True
                        connection_lost = False
                        fail_counter = 0


                    else:
                        logger.info("Соединение стабильно")


                else:
                    fail_counter += 1


                    logger.warning(f"Проблема с интернетом ({fail_counter})")


                    if process_status:
                        stop_all()


                        process_status = False


                    connection_lost = True

                
                sleep_time = CHECK_INTERVAL


                time.sleep(sleep_time)


            except KeyboardInterrupt:
                raise


            except Exception as e:
                logger.error(f"[main()] Ошибка: {str(e)}")


                time.sleep(CHECK_INTERVAL)


    except KeyboardInterrupt:
        logger.info("\nЗавершение работы...")


        stop_all()


    except Exception as e:
        logger.error(f"[main()] Фатальная ошибка: {str(e)}")


        stop_all()


if __name__ == "__main__":
    main()