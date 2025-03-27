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


# Logger setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


logger = logging.getLogger(__name__)


# Database configuration
db = DataBaze('.')
config = db.file('config')


# Create config if not exists
if config.create() == True:
    config.write({
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
                    "telegram_bot.py"
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
    })
    

    logger.warning('Please fill in the data in config.json')


    quit()


# Config operations
def get_config() -> dict:
    return config.read()


def update_config(new_config: dict) -> None:
    config.write(new_config)


# Get ignored folders
def get_ignore_folders() -> list:
    ignore_folders = get_config().get('system', {}).get('ignore_folders', [])


    if ignore_folders != []:
        return ignore_folders
    

    return []


# Constants
CHECK_INTERVAL = 180
PROCESS_IDS = {}
IGNORE_FOLDERS = get_ignore_folders()
PM2_CMD = "pm2.cmd" if platform.system() == "Windows" else "pm2"


# Internet connection check
def check_internet() -> bool:
    """Check internet connection using combination of methods."""
    result = 0


    # Socket connection check
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


    # Ping check
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


# PM2 output processing
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
                logger.error(f'[parse_autorun()] File not found: {full_path}')
                

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


                        logger.info(f"Successfully started process: {file_name} (ID: {proc[0]})")


                        break


            except subprocess.CalledProcessError as e:
                logger.error(f"[parse_autorun()] Error starting {file_name}: {e.stderr}")


            except json.JSONDecodeError:
                logger.error("[parse_autorun()] PM2 output parsing error")


    except Exception as e:
        logger.error(f"[parse_autorun()] Folder processing error: {str(e)}")


    return processes


def terminate_process(process_id: str) -> None:
    """Stop process with ID validation"""
    if process_id is None:
        logger.error("[terminate_process()] Invalid process ID")


        return

    try:
        subprocess.run(
            [PM2_CMD, "stop", str(process_id)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            encoding='utf-8'
        )


        logger.info(f"Process {process_id} stopped")


    except subprocess.CalledProcessError as e:
        logger.error(f"[terminate_process()] Error stopping {process_id}: {e.stderr}")


def stop_all() -> None:
    """Stop all processes and clear dictionary"""
    for name, pid in list(PROCESS_IDS.items()):
        terminate_process(str(pid))


        del PROCESS_IDS[name]


def start_all() -> None:
    """Start processes with encoding handling"""
    logger.info('Starting processes')


    for item in get_config().get('system', {}).get('autorun', {}):
        folder = os.path.join(os.getcwd(), item)


        if os.path.isdir(folder) and folder.replace(os.getcwd()+'\\', '') not in IGNORE_FOLDERS \
            and get_config().get('system', {}).get('autorun', {}).get(item, []) != []:
            parse_autorun(folder, get_config().get('system', {}).get('autorun', {}).get(item, []))


def main():
    connection_lost = False
    fail_counter = 0

    try:
        logger.info("System initialization...")


        start_all()


        process_status = True

        
        while True:
            try:
                if check_internet():
                    if connection_lost:
                        logger.info("Connection restored! Restarting services...")


                        start_all()


                        process_status = True
                        connection_lost = False
                        fail_counter = 0


                    else:
                        logger.info("Connection stable")


                else:
                    fail_counter += 1


                    logger.warning(f"Internet connection issue ({fail_counter})")


                    if process_status:
                        stop_all()


                        process_status = False


                    connection_lost = True

                
                sleep_time = CHECK_INTERVAL


                time.sleep(sleep_time)


            except KeyboardInterrupt:
                raise


            except Exception as e:
                logger.error(f"[main()] Error: {str(e)}")


                time.sleep(CHECK_INTERVAL)


    except KeyboardInterrupt:
        logger.info("Shutting down...")


        stop_all()


    except Exception as e:
        logger.error(f"[main()] Fatal error: {str(e)}")


        stop_all()


if __name__ == "__main__":
    main()
